// While developing, the website runs on port 5173 and the Flask backend on port 5000.
// This forwards every /api/... call from the website to Flask, so no extra setup is needed.
export default {
  server: {
    proxy: { '/api': 'http://localhost:5000' },
  },
};
