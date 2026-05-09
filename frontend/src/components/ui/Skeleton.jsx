import React from "react";

export function Skeleton({ className, ...props }) {
  return (
    <div
      className={`skeleton-pulse ${className || ""}`}
      style={{
        width: "100%",
        minHeight: "1.25rem",
        ...props.style
      }}
      {...props}
    />
  );
}
