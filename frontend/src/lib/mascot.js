import { BACKEND_URL } from "@/lib/api";

// Versions WebP légères générées à côté des PNG : sm = 160 px, md = 640 px.
export const mascotSrc = (path, size = "md") =>
  `${BACKEND_URL}${path.replace("/mascots/", `/mascots/${size}/`).replace(/\.png$/, ".webp")}`;
