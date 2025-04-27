import React from 'react';

const Home = ({ onQRScan }) => {
  return (
    <div className="flex flex-col items-center justify-center h-screen p-4">
      <h1 className="text-2xl font-bold mb-4">Tap to Unlock</h1>
      <img src="/logo.png" alt="Logo" className="w-16 h-16 mb-4" />
      <button
        className="bg-blue-500 text-white px-4 py-2 rounded-lg text-lg"
        onClick={onQRScan}
        aria-label="Scan QR Code"
      >
        Scan QR Code
      </button>
      <p className="text-gray-500 mt-2">Ready to Unlock</p>
    </div>
  );
};

export default Home;
