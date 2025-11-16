use std::ffi::OsString;
use std::os::windows::ffi::OsStringExt;
use std::thread;
use std::time::Duration;
use std::mem;
use std::ffi::c_void;

use windows::core::*;
use windows::Win32::Foundation::*;
use windows::Win32::System::Ioctl::*;
use windows::Win32::System::IO::*;
use windows::Win32::Storage::FileSystem::{
    CreateFileW,
    GetDriveTypeW,
    GetVolumeInformationW,
    FILE_SHARE_READ,
    FILE_SHARE_WRITE,
    OPEN_EXISTING,
    FILE_ATTRIBUTE_NORMAL,
    FILE_FLAG_OVERLAPPED,
    FILE_FLAGS_AND_ATTRIBUTES,
};

// Drive type constants
const DRIVE_FIXED: u32 = 3;
const DRIVE_REMOVABLE: u32 = 2;

// GetLogicalDrives function - using Windows API directly
#[link(name = "kernel32")]
extern "system" {
    fn GetLogicalDrives() -> u32;
}

// Wrapper to make raw pointer Send (Windows handles are thread-safe)
struct SendPtr(*mut c_void);
unsafe impl Send for SendPtr {}

impl SendPtr {
    fn into_handle(self) -> HANDLE {
        HANDLE(self.0)
    }
}

fn main() {
    println!("=== NTFS USN Journal Realtime Monitor (Rust) ===");
    println!("Monitoring for file system changes...\n");

    unsafe {
        let drives_mask = GetLogicalDrives();
        for i in 0..26 {
            if (drives_mask & (1 << i)) == 0 {
                continue;
            }

            // build root like "C:\\"
            let mut root = vec![
                (b'A' + i as u8) as u16,
                b':' as u16,
                b'\\' as u16,
                0u16,
            ];

            let drive_type = GetDriveTypeW(PWSTR(root.as_mut_ptr()));
            if drive_type != DRIVE_FIXED && drive_type != DRIVE_REMOVABLE {
                continue;
            }

            // Detect FS type (filesystem name buffer)
            let mut fsname: [u16; 32] = [0; 32];
            let res = GetVolumeInformationW(
                PWSTR(root.as_mut_ptr()),
                None,
                None,
                None,
                None,
                Some(&mut fsname),
            );

            if res.is_err() {
                continue;
            }

            let fs = OsString::from_wide(&fsname);
            if fs.to_string_lossy().trim_matches('\u{0}') != "NTFS" {
                continue;
            }

            let device_path = format!(r"\\.\{}:", (b'A' + i as u8) as char);
            println!("✓ Opening NTFS volume {}", device_path);

            // Create null-terminated wide string for CreateFileW
            let mut device_path_wide: Vec<u16> = device_path.encode_utf16().chain(std::iter::once(0)).collect();

            // KEY FIX: Proper type casting for FILE_FLAGS_AND_ATTRIBUTES
            let handle = CreateFileW(
                PWSTR(device_path_wide.as_mut_ptr()),
                (GENERIC_READ.0 | GENERIC_WRITE.0) as u32,
                FILE_SHARE_READ | FILE_SHARE_WRITE,
                None,
                OPEN_EXISTING,
                FILE_FLAGS_AND_ATTRIBUTES(FILE_ATTRIBUTE_NORMAL.0 | FILE_FLAG_OVERLAPPED.0),
                None,
            );

            if let Ok(h) = handle {
                let h_raw = h.0;
                let h_send = SendPtr(h_raw);
                thread::spawn(move || {
                    let h_reconstructed = h_send.into_handle();
                    unsafe {
                        tail_volume(h_reconstructed, device_path);
                    }
                });
            } else {
                eprintln!("✗ Failed to open {}: {:?}", device_path, handle.err());
            }
        }
    }

    // Keep main alive forever
    loop {
        thread::sleep(Duration::from_secs(1));
    }
}

unsafe fn tail_volume(h: HANDLE, vol_name: String) {
    println!("[{}] Querying USN journal...", vol_name);

    let mut data: USN_JOURNAL_DATA_V0 = mem::zeroed();
    let mut bytes_returned: u32 = 0;

    let q = DeviceIoControl(
        h,
        FSCTL_QUERY_USN_JOURNAL,
        None,
        0,
        Some(&mut data as *mut _ as *mut c_void),
        mem::size_of::<USN_JOURNAL_DATA_V0>() as u32,
        Some(&mut bytes_returned as *mut u32),
        None,
    );

    if let Err(err) = q {
        eprintln!("[{}] FSCTL_QUERY_USN_JOURNAL failed: {:?}", vol_name, err);
        return;
    }

    println!("[{}] JournalID={} NextUSN={}", vol_name, data.UsnJournalID, data.NextUsn);
    println!("[{}] ⏳ Waiting for real-time changes...\n", vol_name);

    // KEY FIX: Use blocking mode with BytesToWaitFor
    let mut read_data = READ_USN_JOURNAL_DATA_V0 {
        StartUsn: data.NextUsn,
        ReasonMask: 0xFFFFFFFF,
        ReturnOnlyOnClose: 0,
        Timeout: 0,                    // Infinite timeout - wait forever
        BytesToWaitFor: 1,             // Wait for at least 1 byte of new data
        UsnJournalID: data.UsnJournalID,
    };

    let mut buffer = vec![0u8; 64 * 1024]; // 64KB buffer

    loop {
        let mut bytes: u32 = 0;

        // This will BLOCK until new changes occur
        let r = DeviceIoControl(
            h,
            FSCTL_READ_USN_JOURNAL,
            Some(&read_data as *const _ as *const c_void),
            mem::size_of::<READ_USN_JOURNAL_DATA_V0>() as u32,
            Some(buffer.as_mut_ptr() as *mut c_void),
            buffer.len() as u32,
            Some(&mut bytes as *mut u32),
            None,
        );

        if let Err(err) = r {
            let error_code = err.code();
            let code_value = error_code.0;
            
            // ERROR_HANDLE_EOF means journal wrapped or was deleted
            if code_value == 38 {
                eprintln!("[{}] Journal wrapped or EOF reached, re-querying...", vol_name);
                
                // Re-query to get new starting point
                let mut new_data: USN_JOURNAL_DATA_V0 = mem::zeroed();
                let mut bytes_ret: u32 = 0;
                
                let q2 = DeviceIoControl(
                    h,
                    FSCTL_QUERY_USN_JOURNAL,
                    None,
                    0,
                    Some(&mut new_data as *mut _ as *mut c_void),
                    mem::size_of::<USN_JOURNAL_DATA_V0>() as u32,
                    Some(&mut bytes_ret as *mut u32),
                    None,
                );
                
                if q2.is_ok() {
                    read_data.StartUsn = new_data.NextUsn;
                    read_data.UsnJournalID = new_data.UsnJournalID;
                    continue;
                } else {
                    thread::sleep(Duration::from_secs(1));
                    continue;
                }
            }
            
            eprintln!("[{}] DeviceIoControl error: {:?} (code: {})", vol_name, err, code_value);
            thread::sleep(Duration::from_millis(500));
            continue;
        }

        // Check if we got any data
        if bytes <= mem::size_of::<i64>() as u32 {
            continue;
        }

        // Parse USN records from buffer
        // First 8 bytes is the next USN to read from
        let next_usn = *(buffer.as_ptr() as *const i64);
        
        let mut offset = mem::size_of::<i64>();
        while offset + mem::size_of::<USN_RECORD_V2>() <= bytes as usize {
            let rec = &*(buffer[offset..].as_ptr() as *const USN_RECORD_V2);

            if rec.RecordLength == 0 || offset + rec.RecordLength as usize > bytes as usize {
                break;
            }

            // Extract filename
            let name_offset = offset + rec.FileNameOffset as usize;
            let name_len_u16 = (rec.FileNameLength / 2) as usize;

            if name_offset + (name_len_u16 * 2) > bytes as usize {
                break;
            }

            let name_ptr = buffer[name_offset..].as_ptr() as *const u16;
            let name_slice = std::slice::from_raw_parts(name_ptr, name_len_u16);
            let name = OsString::from_wide(name_slice).to_string_lossy().to_string();

            let timestamp = format_timestamp();

            // Color-coded output based on operation type
            let icon = if rec.Reason & USN_REASON_FILE_CREATE != 0 {
                "✨ CREATE"
            } else if rec.Reason & USN_REASON_FILE_DELETE != 0 {
                "🗑️  DELETE"
            } else if rec.Reason & USN_REASON_RENAME_NEW_NAME != 0 {
                "📝 RENAME"
            } else if rec.Reason & (USN_REASON_DATA_OVERWRITE | USN_REASON_DATA_EXTEND) != 0 {
                "✏️  MODIFY"
            } else {
                "📄 CHANGE"
            };

            println!("[{}] {} | {} | USN={} | FileRef={:016X}", 
                timestamp, icon, name, rec.Usn, rec.FileReferenceNumber);

            offset += rec.RecordLength as usize;
        }

        // Update starting position for next read
        read_data.StartUsn = next_usn;
    }
}

fn format_timestamp() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    
    let duration = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap();
    
    let total_secs = duration.as_secs();
    let millis = duration.subsec_millis();
    
    // Calculate hours, minutes, seconds
    let hours = (total_secs / 3600) % 24;
    let minutes = (total_secs / 60) % 60;
    let seconds = total_secs % 60;
    
    format!("{:02}:{:02}:{:02}.{:03}", hours, minutes, seconds, millis)
}