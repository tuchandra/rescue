module.exports = {
  theme: {
    extend: {},
    container: {
      center: true,
    },
  },
  variants: {},
  plugins: [
    require("@tailwindcss/custom-forms")
  ],
  purge: [
    'index.html',
    'js/script.js',
    'tailwind.config.js',
    'tailwind.css',
  ],
}
