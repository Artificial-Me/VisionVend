import { useState } from 'react'
import { Button } from './components/ui/button'
import { StatusIndicator } from './components/StatusIndicator'
import './App.css'

const initialStatus = {
  nfc: 'idle',
  door: 'idle',
  transaction: 'idle',
  training: 'idle',
}

function App() {
  const [status, setStatus] = useState(initialStatus)
  const [log, setLog] = useState([])
  const [count, setCount] = useState(0)

  const handleTapToPay = () => {
    setStatus(s => ({ ...s, nfc: 'success', door: 'info' }))
    setLog(l => [...l, 'NFC tap received. Door unlocked.'])
  }

  const handleOpenDoor = () => {
    setStatus(s => ({ ...s, door: 'success' }))
    setLog(l => [...l, 'Door opened.'])
  }

  const handleTrackLogProducts = () => {
    setStatus(s => ({ ...s, transaction: 'info' }))
    setLog(l => [...l, 'Tracking/logging products...'])
    setTimeout(() => {
      setStatus(s => ({ ...s, transaction: 'success' }))
      setLog(l => [...l, 'Products removed. Transaction successful.'])
    }, 1200)
  }

  const handleCloseDoor = () => {
    setStatus(s => ({ ...s, door: 'idle', nfc: 'idle', transaction: 'idle' }))
    setLog(l => [...l, 'Door closed. Ready for next customer.'])
  }

  const handleTrain = () => {
    setStatus(s => ({ ...s, training: 'info' }))
    setLog(l => [...l, 'Training started...'])
    setTimeout(() => {
      const success = Math.random() > 0.2
      setStatus(s => ({ ...s, training: success ? 'success' : 'error' }))
      setLog(l => [
        ...l,
        success ? 'Training successful!' : 'Training failed. Try again.'
      ])
    }, 1800)
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center py-8">
      <h1 className="text-3xl font-bold mb-4">VisionVend Simulator</h1>
      <div className="flex flex-col md:flex-row gap-8 w-full max-w-3xl">
        {/* Customer Panel */}
        <div className="flex-1 bg-white rounded-lg shadow-md p-6 mb-6 md:mb-0">
          <h2 className="text-xl font-semibold mb-4">Customer Flow</h2>
          <div className="flex flex-col gap-3 mb-6">
            <Button onClick={handleTapToPay} className="w-full">Tap-to-Pay</Button>
            <Button onClick={handleOpenDoor} className="w-full">Open Door</Button>
            <Button onClick={handleTrackLogProducts} className="w-full">Track/Log Products</Button>
            <Button onClick={handleCloseDoor} className="w-full">Close Door</Button>
          </div>
          <div className="mb-2">
            <StatusIndicator label="NFC Tap" status={status.nfc} />
            <StatusIndicator label="Door Status" status={status.door} />
            <StatusIndicator label="Transaction" status={status.transaction} />
          </div>
        </div>
        {/* Owner Panel */}
        <div className="flex-1 bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Owner/Operator</h2>
          <Button onClick={handleTrain} className="w-full mb-3">Train</Button>
          <StatusIndicator label="Training Status" status={status.training} />
        </div>
      </div>
      {/* Log output */}
      <div className="w-full max-w-3xl mt-8 bg-white rounded-lg shadow p-4">
        <h3 className="font-semibold mb-2">Event Log</h3>
        <ul className="text-sm text-gray-700 space-y-1">
          {log.slice(-8).map((msg, i) => (
            <li key={i}>• {msg}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default App
