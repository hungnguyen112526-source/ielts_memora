// Cấu hình Tailwind cho engine làm bài. Chạy tools/tailwind/build.sh sau khi sửa class trong engine/reader/index.html.
module.exports = {
  darkMode: 'class',
  content: ['../../engine/reader/index.html'],
  theme: { extend: { fontFamily: { sans: ['Inter', 'sans-serif'] } } },
};
