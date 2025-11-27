import { useState } from 'react';
import axios from 'axios';
import Head from 'next/head';

export default function Home() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searched, setSearched] = useState(false);
  const [searchPrompt, setSearchPrompt] = useState('');

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    
    setLoading(true);
    setError(null);
    setSearched(true);
    setSearchPrompt(`Searching for "${query}" related documents...`);
    
    try {
      const response = await axios.get(`${API_URL}/search`, {
        params: { query, limit: 20 }
      });
      setResults(response.data.results || []);
      setSearchPrompt('');
    } catch (err) {
      setError('Search failed. Please try again.');
      setSearchPrompt('');
      console.error('Search error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (docId, fileName) => {
    try {
      const response = await axios.get(`${API_URL}/documents/${docId}/download`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName || `${docId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Download failed. Please try again.');
      console.error('Download error:', err);
    }
  };

  return (
    <>
      <Head>
        <title>Wood AI Internal Document Search Engine</title>
        <meta name="description" content="Wood AI-powered internal document search" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      
      <div className="flex flex-col min-h-screen bg-gradient-to-br from-woods-light to-white">
        {/* Header */}
        <div className="bg-woods-primary text-white shadow-lg">
          <div className="max-w-6xl mx-auto px-4 py-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold">Wood AI</h1>
                <p className="text-woods-secondary text-sm mt-1">Internal Document Search Engine</p>
              </div>
              <div className="text-sm text-gray-300">
                POC Version 1.0
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-grow max-w-6xl w-full mx-auto px-4 py-8">
          {/* Search Bar */}
          <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
            <form onSubmit={handleSearch}>
              <div className="flex flex-col gap-4">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder='Search documents... (e.g., "corrosion", "safety", "inspection")'
                    className="flex-1 px-4 py-3 border-2 border-woods-secondary/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-woods-secondary focus:border-transparent text-gray-800"
                  />
                  <button
                    type="submit"
                    disabled={loading}
                    className="px-8 py-3 bg-woods-secondary text-white font-semibold rounded-lg hover:bg-woods-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? (
                      <span className="flex items-center gap-2">
                        <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Searching
                      </span>
                    ) : 'Search'}
                  </button>
                </div>
                
                {/* Search Tips */}
                <div className="text-sm text-gray-600">
                  <span className="font-semibold text-woods-primary">Search Tips:</span> Use keywords like "corrosion", "inspection", "safety" to find relevant documents. Fuzzy matching enabled.
                </div>
              </div>
            </form>
          </div>

          {/* Search Prompt Message */}
          {searchPrompt && (
            <div className="bg-woods-secondary/10 border-l-4 border-woods-secondary rounded-lg p-4 mb-6 animate-pulse">
              <div className="flex items-center gap-3">
                <svg className="animate-spin h-5 w-5 text-woods-secondary" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <p className="text-woods-primary font-medium">{searchPrompt}</p>
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 border-l-4 border-red-500 rounded-lg p-4 mb-6">
              <p className="text-red-700 font-medium">{error}</p>
            </div>
          )}

          {/* No Results */}
          {searched && results.length === 0 && !loading && !error && (
            <div className="bg-yellow-50 border-l-4 border-yellow-500 rounded-lg p-6 text-center">
              <p className="text-yellow-800 font-medium">No documents found for "{query}"</p>
              <p className="text-yellow-700 text-sm mt-2">Try different keywords or check if documents are ingested.</p>
            </div>
          )}

          {/* Results */}
          {results.length > 0 && (
            <div>
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-xl font-semibold text-woods-primary">
                  Found {results.length} document{results.length !== 1 ? 's' : ''}
                </h2>
              </div>
              
              <div className="space-y-4">
                {results.map((doc, idx) => (
                  <div key={idx} className="bg-white rounded-lg shadow-md hover:shadow-xl transition-shadow border-l-4 border-woods-secondary">
                    <div className="p-6">
                      {/* Document Title */}
                      <div className="flex items-start justify-between gap-4">
                        <h3 className="text-xl font-semibold text-woods-primary flex-1">
                          {doc.title}
                        </h3>
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-woods-secondary/10 text-woods-secondary">
                          {doc.file_type?.toUpperCase() || 'PDF'}
                        </span>
                      </div>

                      {/* Snippet */}
                      {doc.snippet && (
                        <div className="mt-3 text-gray-700">
                          <p className="line-clamp-3" dangerouslySetInnerHTML={{ __html: doc.snippet }}></p>
                        </div>
                      )}

                      {/* Score & Metadata */}
                      <div className="mt-4 flex items-center gap-4 text-sm text-gray-600">
                        <span className="flex items-center gap-1">
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
                          </svg>
                          Relevance: {doc.score?.toFixed(2)}
                        </span>
                        <span>•</span>
                        <span>{doc.file_path?.split('/').pop() || 'Document'}</span>
                      </div>

                      {/* Actions */}
                      <div className="mt-4 pt-4 border-t border-gray-200 flex gap-3">
                        <button
                          onClick={() => handleDownload(doc.id, `${doc.title}.pdf`)}
                          className="inline-flex items-center gap-2 px-4 py-2 bg-woods-primary text-white rounded-lg hover:bg-woods-dark transition-colors"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                          Download PDF
                        </button>
                        <a
                          href={`${API_URL}${doc.download_url}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-2 px-4 py-2 border-2 border-woods-secondary text-woods-secondary rounded-lg hover:bg-woods-secondary hover:text-white transition-colors"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                          </svg>
                          View Details
                        </a>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer - Fixed at bottom */}
        <div className="mt-auto bg-woods-dark text-white py-6">
          <div className="max-w-6xl mx-auto px-4 text-center">
            <p className="text-sm text-gray-400">
              Wood AI Internal Document Search Engine • Built with FastAPI, Elasticsearch & Next.js
            </p>
            <p className="text-xs text-gray-500 mt-2">
              For internal use only • {new Date().getFullYear()}
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
