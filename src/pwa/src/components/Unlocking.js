import React from 'react';

const Unlocking = () => {
  return (
    <div className="flex flex-col items-center justify-center h-screen p-4">
      <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mb-4"></div>
      <h1 className="text-xl font-bold">Unlocking...</h1>
      <button className="text-red-500 mt-4" aria-label="Cancel">Cancel</button>
    </div>
  );
};

export default Unlocking;
