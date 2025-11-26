import { useState } from 'react';
import axios from 'axios';
import Head from 'next/head';

export default function Home() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searched, setSearched] = useState(false);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    
    setLoading(true);
    setError(null);
    setSearched(true);
    
    try {
      const response = await axios.get(`${API_URL}/search`, {
        params: { query, limit: 20 }
      });
      setResults(response.data.results || []);
    } catch (err) {
      setError('Search failed. Please try again.');
      console.error('Search error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (docId, format) => {
    try {
      const response = await axios.get(`${API_URL}/export/${docId}`, {
        params: { format },
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = `document.${format}`;
      link.click();
    } catch (err) {
      alert('Export failed');
    }
  };

  return (
    <>
      <Head>
        <title>Woods Document Search</title>
        <meta name="description" content="Search Woods internal documents" />
      </Head>
      <div className="min-h-screen bg-gray-50 py-8 px-4">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold text-center text-gray-800 mb-8">
            Woods Document Search
          </h1>
          <form onSubmit={handleSearch} className="mb-8">
            <div className="flex gap-2">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search documents by keyword..."
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Searching...' : 'Search'}
              </button>
            </div>
          </form>
          {error && <div className="text-red-600 text-center mb-4">{error}</div>}
          {searched && results.length === 0 && !loading && (
            <div className="text-gray-600 text-center">No results found</div>
          )}
          <div className="space-y-4">
            {results.map((doc, idx) => (
              <div key={idx} className="bg-white p-4 rounded-lg shadow border">
                <h2 className="text-xl font-semibold text-blue-600">{doc.title}</h2>
                <p className="text-gray-600 mt-2">{doc.excerpt}</p>
                <div className="mt-3 flex gap-2">
                  <button onClick={() => handleExport(doc.id, 'pdf')} className="text-sm text-blue-600 hover:underline">Export PDF</button>
                  <button onClick={() => handleExport(doc.id, 'docx')} className="text-sm text-blue-600 hover:underline">Export DOCX</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
