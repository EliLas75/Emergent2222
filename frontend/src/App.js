import React, { useState, useRef } from 'react';
import './App.css';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [dragActive, setDragActive] = useState(false);
  const [uploadedData, setUploadedData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    const files = e.dataTransfer.files;
    if (files && files[0]) {
      handleFile(files[0]);
    }
  };

  const handleFileInput = (e) => {
    const file = e.target.files[0];
    if (file) {
      handleFile(file);
    }
  };

  const handleFile = async (file) => {
    if (!file.name.endsWith('.csv')) {
      setError('Veuillez sélectionner un fichier CSV');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(`${API}/upload-csv`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setUploadedData(response.data);
    } catch (err) {
      setError('Erreur lors du traitement du fichier. Vérifiez le format CSV.');
      console.error('Upload error:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatNumber = (num) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'decimal',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(num);
  };

  const formatPercentage = (num) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'percent',
      minimumFractionDigits: 1,
      maximumFractionDigits: 1
    }).format(num / 100);
  };

  const KPICard = ({ title, value, type = 'currency', trend, icon }) => {
    const formattedValue = type === 'percentage' 
      ? formatPercentage(value) 
      : formatNumber(value) + ' €';
    
    const trendColor = trend >= 0 ? 'text-green-500' : 'text-red-500';
    
    return (
      <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100 hover:shadow-xl transition-shadow duration-300">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <span className="text-2xl">{icon}</span>
            <h3 className="text-sm font-medium text-gray-600">{title}</h3>
          </div>
          {trend !== undefined && (
            <span className={`text-sm font-medium ${trendColor}`}>
              {trend >= 0 ? '+' : ''}{formatPercentage(Math.abs(trend))}
            </span>
          )}
        </div>
        <p className="text-2xl font-bold text-gray-900">{formattedValue}</p>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Analyse Financière SaaS
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Glissez-déposez votre fichier CSV de données financières pour obtenir instantanément 
            vos KPI essentiels et un dashboard interactif.
          </p>
        </div>

        {/* Upload Area */}
        {!uploadedData && (
          <div className="max-w-2xl mx-auto mb-12">
            <div
              className={`relative border-2 border-dashed rounded-xl p-12 text-center transition-colors duration-200 
                ${dragActive 
                  ? 'border-blue-500 bg-blue-50' 
                  : 'border-gray-300 hover:border-gray-400'
                }
                ${loading ? 'pointer-events-none opacity-75' : 'cursor-pointer'}
              `}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                onChange={handleFileInput}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
              
              {loading ? (
                <div className="flex flex-col items-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mb-4"></div>
                  <p className="text-lg text-gray-600">Traitement en cours...</p>
                </div>
              ) : (
                <>
                  <div className="text-6xl mb-4">📊</div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">
                    Glissez votre fichier CSV ici
                  </h3>
                  <p className="text-gray-600 mb-4">
                    ou cliquez pour sélectionner un fichier
                  </p>
                  <div className="text-sm text-gray-500">
                    Formats supportés : revenus, charges, EBITDA, cash flow, etc.
                  </div>
                </>
              )}
            </div>
            
            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
                {error}
              </div>
            )}
          </div>
        )}

        {/* Dashboard */}
        {uploadedData && (
          <div className="max-w-7xl mx-auto">
            {/* File Info */}
            <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">
                    📈 Analyse : {uploadedData.filename}
                  </h2>
                  <p className="text-gray-600 mt-1">
                    Colonnes détectées : {Object.keys(uploadedData.detected_columns).length}
                  </p>
                </div>
                <button
                  onClick={() => {
                    setUploadedData(null);
                    setError(null);
                  }}
                  className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-gray-700 transition-colors duration-200"
                >
                  Nouveau fichier
                </button>
              </div>
            </div>

            {/* KPI Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6 mb-8">
              <KPICard
                title="Revenus Totaux"
                value={uploadedData.kpis.revenus_totaux}
                icon="💰"
                trend={5.2}
              />
              <KPICard
                title="EBITDA"
                value={uploadedData.kpis.ebitda}
                icon="📊"
                trend={3.1}
              />
              <KPICard
                title="Résultat Net"
                value={uploadedData.kpis.resultat_net}
                icon="💵"
                trend={-1.2}
              />
              <KPICard
                title="Free Cash Flow"
                value={uploadedData.kpis.free_cash_flow}
                icon="💸"
                trend={8.7}
              />
              <KPICard
                title="Marge Nette"
                value={uploadedData.kpis.marge_nette}
                type="percentage"
                icon="📈"
                trend={2.3}
              />
            </div>

            {/* Detected Columns */}
            <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
              <h3 className="text-xl font-bold text-gray-900 mb-4">
                🔍 Colonnes Détectées
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(uploadedData.detected_columns).map(([key, value]) => (
                  <div key={key} className="bg-gray-50 rounded-lg p-3">
                    <div className="font-medium text-gray-900 capitalize">
                      {key.replace('_', ' ')}
                    </div>
                    <div className="text-sm text-gray-600">→ {value}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Data Preview */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h3 className="text-xl font-bold text-gray-900 mb-4">
                📋 Aperçu des Données
              </h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      {uploadedData.data_preview && uploadedData.data_preview[0] && 
                        Object.keys(uploadedData.data_preview[0]).map((key) => (
                        <th key={key} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          {key}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {uploadedData.data_preview && uploadedData.data_preview.slice(0, 5).map((row, idx) => (
                      <tr key={idx}>
                        {Object.values(row).map((cell, cellIdx) => (
                          <td key={cellIdx} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;