/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        leaf: { 50: '#f0fdf4', 100: '#dcfce7', 500: '#24925a', 600: '#157746', 700: '#0e5c35' },
        soil: '#744a2d',
      },
      boxShadow: { soft: '0 12px 30px rgba(21, 119, 70, 0.10)' },
    },
  },
  plugins: [],
}
