import React from 'react';
// import config from '../config';

const Transaction = ({ transaction }) => {
  return (
    <div className="flex flex-col items-center justify-center h-screen p-4">
      <h1 className="text-2xl font-bold mb-4">Transaction</h1>
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
      </div>
      <p className="text-gray-500 mt-4">Door Open</p>
    </div>
  );
};

export default Transaction;
