import { memo } from "react";

export const Skeleton = memo(function Skeleton({
  width = "100%",
  height = 16,
  rounded = true,
  className,
}: {
  width?: number | string;
  height?: number | string;
  rounded?: boolean;
  className?: string;
}) {
  return (
    <span
      aria-hidden="true"
      className={`skeleton ${rounded ? "skeleton-rounded" : ""} ${className ?? ""}`}
      style={{ width, height }}
    />
  );
});

export const SkeletonBlock = memo(function SkeletonBlock({
  rows = 3,
  rowHeight = 14,
  gap = 8,
}: {
  rows?: number;
  rowHeight?: number;
  gap?: number;
}) {
  return (
    <div className="skeleton-block" style={{ gap }}>
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} height={rowHeight} width={i === rows - 1 ? "60%" : "100%"} />
      ))}
    </div>
  );
});
