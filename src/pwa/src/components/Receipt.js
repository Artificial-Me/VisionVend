import React from 'react';
// import config from '../config';

const Receipt = ({ transaction }) => {
  const handleSave = () => {
    // Generate PDF (e.g., jsPDF)
    alert('Receipt saved');
  };

  const handleEmail = () => {
    // Send via server
    alert('Receipt emailed');
  };

  return (
    <div className="flex flex-col items-center justify-center h-screen p-4">
      <h1 className="text-2xl font-bold mb-4">Thank You!</h1>
      <div className="w-80">
        {transaction.items.map((item, index) => (
          <div key={index} className="flex justify-between p-2 bg-gray-100 odd:bg-white">
            <span>{item}</span>
            {/* <span>${config.inventory[item]?.price.toFixed(2)}</span> */}
            <span>$0.00</span>
          </div>
        ))}
        <div className="flex justify-between p-2 mt-2 border-t">
          <span className="font-bold">Total</span>
          <span className="font-bold text-green-500">${transaction.total.toFixed(2)}</span>
        </div>
        <p className="text-gray-500 mt-2">{new Date().toLocaleString()}</p>
      </div>
      <button
        className="bg-blue-500 text-white px-4 py-2 rounded-lg mt-4"
        onClick={handleSave}
        aria-label="Save Receipt"
      >
        Save Receipt
      </button>
      <button
        className="bg-blue-500 text-white px-4 py-2 rounded-lg mt-2"
        onClick={handleEmail}
        aria-label="Email Receipt"
      >
        Email Receipt
      </button>
    </div>
  );
};

export default Receipt;
