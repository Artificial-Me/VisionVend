import React from 'react'

export function StatusIndicator({ label, status }) {
  const statusColor = {
    success: "bg-green-500",
    error: "bg-red-500",
    warning: "bg-yellow-400",
    info: "bg-blue-500",
    idle: "bg-gray-400",
  }[status] || "bg-gray-400";

  return (
    <div className="flex items-center gap-2 mb-2">
      <div className={`${statusColor} w-3 h-3 rounded-full mr-2`} />
      <span className="text-sm font-medium">{label}</span>
    </div>
  );
}
