module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        woods: {
          primary: '#003E52',    // Woods dark blue
          secondary: '#00A79D',  // Woods teal/green
          accent: '#F58220',     // Woods orange accent
          dark: '#002B36',       // Dark blue
          light: '#E8F4F8',      // Light blue background
        },
      },
    },
  },
  plugins: [],
}
