import { useEffect, useState } from 'react'
import FarmerAssistant from './pages/FarmerAssistant'
import ExpertDashboard from './pages/ExpertDashboard'
import Marketplace from './pages/Marketplace'

function initialLanguage() {
  return window.localStorage.getItem('rythu-language') === 'en' ? 'en' : 'te'
}

function initialView() {
  try {
    const account = JSON.parse(window.sessionStorage.getItem('rythu-market-account') || 'null')
    const token = window.sessionStorage.getItem('rythu-market-token')
    if (token && account?.account_type === 'farmer') return 'farmer-market'
    if (token && account?.account_type === 'worker') return 'worker-market'
  } catch {
    window.sessionStorage.removeItem('rythu-market-account')
    window.sessionStorage.removeItem('rythu-market-token')
  }
  return 'farmer'
}

export default function App() {
  const [view, setView] = useState(initialView)
  const [language, setLanguage] = useState(initialLanguage)

  useEffect(() => {
    window.localStorage.setItem('rythu-language', language)
    document.documentElement.lang = language === 'en' ? 'en' : 'te'
    document.title = language === 'en' ? 'Rythu Sahay | RYTHU SAHAYA' : 'రీతు సహాయ | RYTHU SAHAYA'
  }, [language])

  const page = view === 'expert'
    ? <ExpertDashboard language={language} onBack={() => setView('farmer')} />
    : view === 'farmer-market'
      ? <Marketplace key="farmer-market" accountType="farmer" language={language} onBack={() => setView('farmer')} />
      : view === 'worker-market'
        ? <Marketplace key="worker-market" accountType="worker" language={language} onBack={() => setView('farmer')} />
        : <FarmerAssistant
            language={language}
            onExpertClick={() => setView('expert')}
            onFarmerLogin={() => setView('farmer-market')}
            onWorkerLogin={() => setView('worker-market')}
          />

  return (
    <>
      <div className="flex items-center justify-end gap-1 border-b border-slate-200 bg-white px-4 py-2" role="group" aria-label="Page language">
        <button type="button" onClick={() => setLanguage('en')} aria-pressed={language === 'en'} className={`rounded-lg px-3 py-1.5 text-sm font-bold ${language === 'en' ? 'bg-leaf-600 text-white' : 'text-slate-600 hover:bg-slate-100'}`}>English</button>
        <button type="button" onClick={() => setLanguage('te')} aria-pressed={language === 'te'} className={`rounded-lg px-3 py-1.5 text-sm font-bold ${language === 'te' ? 'bg-leaf-600 text-white' : 'text-slate-600 hover:bg-slate-100'}`}>తెలుగు</button>
      </div>
      {page}
    </>
  )
}
