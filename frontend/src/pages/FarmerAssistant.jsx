import { useCallback, useState } from 'react'
import { AlertCircle, CheckCircle2, Mic, MicOff, PhoneOff, Send, Volume2 } from 'lucide-react'
import Brand from '../components/Brand'
import Keypad from '../components/Keypad'
import { farmerApi } from '../services/api'
import { useSpeech } from '../hooks/useSpeech'
import { translateTree } from '../i18n'

export default function FarmerAssistant({ onExpertClick, onFarmerLogin, onWorkerLogin, language }) {
  const [sessionId, setSessionId] = useState(null)
  const [consent, setConsent] = useState(false)
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const [caseId, setCaseId] = useState(null)
  const [caseAccessToken, setCaseAccessToken] = useState(null)
  const [photoStatus, setPhotoStatus] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [feedbackDone, setFeedbackDone] = useState(false)

  const addMessage = useCallback((speaker, text) => setMessages((current) => [...current, { speaker, text }]), [])
  const { listening, supported, startListening, stopListening, speak } = useSpeech((transcript) => {
    setInput(transcript)
  })

  const startConversation = async () => {
    setError('')
    setBusy(true)
    try {
      const { data } = await farmerApi.start({ consent_recording: consent })
      setSessionId(data.session_id)
      setMessages([{ speaker: 'assistant', text: data.response }])
      speak(data.response)
    } catch {
      setError('సేవతో కనెక్ట్ కాలేకపోయాము. దయచేసి కొద్దిసేపటి తర్వాత ప్రయత్నించండి.')
    } finally { setBusy(false) }
  }

  const sendMessage = async () => {
    const message = input.trim()
    if (!message || !sessionId || busy) return
    setInput('')
    setError('')
    addMessage('farmer', message)
    setBusy(true)
    try {
      const { data } = await farmerApi.message({ session_id: sessionId, message })
      addMessage('assistant', data.response)
      speak(data.response)
      if (data.case_id) {
        setCaseId(data.case_id)
        setCaseAccessToken(data.case_access_token)
      }
    } catch (requestError) {
      const detail = requestError.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'సమాచారం పంపలేకపోయాము. మళ్లీ ప్రయత్నించండి.')
    } finally { setBusy(false) }
  }

  const record = async () => {
    if (!sessionId) { await startConversation(); return }
    if (listening) stopListening()
    else if (!startListening()) setError('ఈ బ్రౌజర్‌లో వాయిస్ గుర్తింపు అందుబాటులో లేదు. దయచేసి టెక్స్ట్ లేదా కీప్యాడ్ ఉపయోగించండి.')
  }

  const endConversation = async () => {
    if (!sessionId) return
    try { await farmerApi.end(sessionId) } finally {
      stopListening(); setSessionId(null); addMessage('assistant', 'సెషన్ ముగిసింది. రికార్డింగ్ నిలిపివేయబడింది.')
    }
  }

  const sendFeedback = async (outcome) => {
    if (!caseId) return
    setBusy(true)
    try {
      await farmerApi.feedback(caseId, { outcome }, caseAccessToken)
      setFeedbackDone(true)
      addMessage('assistant', outcome === 'WORSENED' ? 'మీ సమాచారం నిపుణుడికి అత్యవసర సమీక్ష కోసం పంపించాము.' : 'మీ స్పందన నమోదు చేశాము. ధన్యవాదాలు.')
    } catch { setError('మీ స్పందన నమోదు కాలేదు. దయచేసి మళ్లీ ప్రయత్నించండి.') } finally { setBusy(false) }
  }

  const uploadPhoto = async (event) => {
    const photo = event.target.files?.[0]
    if (!photo || !caseId || !caseAccessToken) return
    setBusy(true); setPhotoStatus('')
    try {
      await farmerApi.uploadPhoto(caseId, caseAccessToken, photo)
      setPhotoStatus('పంట ఫోటో నమోదు అయింది.')
    } catch (requestError) {
      setPhotoStatus(errorText(requestError, 'ఫోటో నమోదు కాలేదు. JPG, PNG లేదా WebP (5 MB వరకు) ప్రయత్నించండి.'))
    } finally { setBusy(false) }
  }

  const errorText = (requestError, fallback) => {
    const detail = requestError.response?.data?.detail
    return typeof detail === 'string' ? detail : fallback
  }

  return translateTree(language, (
    <main className="min-h-screen bg-gradient-to-b from-leaf-50 via-white to-white px-4 py-5 sm:px-6">
      <div className="mx-auto max-w-xl">
        <header className="mb-7 flex flex-wrap items-center justify-between gap-2"><Brand language={language} /><div className="flex flex-wrap justify-end gap-2"><button onClick={onFarmerLogin} className="rounded-xl bg-leaf-600 px-3 py-2 text-xs font-bold text-white hover:bg-leaf-700">రైతు లాగిన్</button><button onClick={onWorkerLogin} className="rounded-xl border border-leaf-200 bg-white px-3 py-2 text-xs font-bold text-leaf-700 hover:bg-leaf-50">కూలీ లాగిన్</button><button onClick={onExpertClick} className="rounded-xl border border-leaf-200 bg-white px-3 py-2 text-xs font-bold text-leaf-700 hover:bg-leaf-50">నిపుణుల లాగిన్</button></div></header>
        <section className="rounded-3xl bg-white p-5 shadow-soft sm:p-7">
          <div className="mb-5 text-center"><p className="text-2xl font-extrabold text-slate-800">పత్తి పంటకు సహాయం</p><p className="mt-2 text-sm leading-6 text-slate-600">నల్గొండ జిల్లా పత్తి రైతుల కోసం తెలుగు సహాయకుడు</p></div>
          {!sessionId && <div className="mb-5 rounded-2xl bg-amber-50 p-4 text-sm leading-6 text-amber-900"><label className="flex cursor-pointer gap-3"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} className="mt-1 h-4 w-4 accent-green-700" /><span>నా సమస్య వివరాలను నమోదు చేయడానికి మరియు అవసరమైతే ఆడియోను ఉపయోగించడానికి నేను అంగీకరిస్తున్నాను.</span></label><button onClick={startConversation} disabled={busy || !consent} className="mt-3 w-full rounded-xl bg-leaf-600 py-3 font-bold text-white hover:bg-leaf-700 disabled:cursor-not-allowed disabled:bg-slate-300">సహాయం ప్రారంభించండి</button></div>}
          <div aria-live="polite" className="mb-4 max-h-72 min-h-40 space-y-3 overflow-y-auto rounded-2xl bg-slate-50 p-3">
            {!messages.length && <p className="p-6 text-center text-sm text-slate-500">ప్రారంభించడానికి పై బటన్ నొక్కండి.</p>}
            {messages.map((message, index) => <div key={`${message.speaker}-${index}`} className={`flex ${message.speaker === 'farmer' ? 'justify-end' : 'justify-start'}`}><div className={`max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-6 ${message.speaker === 'farmer' ? 'bg-leaf-600 text-white' : 'bg-white text-slate-700 shadow-sm'}`}>{message.text}{message.speaker === 'assistant' && <button aria-label="మళ్లీ వినండి" onClick={() => speak(message.text)} className="ml-2 inline-block align-middle text-leaf-600"><Volume2 size={16} /></button>}</div></div>)}
            {busy && <p className="text-center text-sm font-medium text-leaf-700">సమాధానం సిద్ధం అవుతోంది…</p>}
          </div>
          {error && <div className="mb-4 flex gap-2 rounded-xl bg-rose-50 p-3 text-sm text-rose-800"><AlertCircle className="shrink-0" size={18} />{error}</div>}
          <div className="mb-4 flex justify-center"><button onClick={record} disabled={busy || !sessionId} aria-label={listening ? 'రికార్డింగ్ ఆపండి' : 'మాట్లాడండి'} className={`grid h-24 w-24 place-items-center rounded-full text-white shadow-xl transition ${listening ? 'animate-pulse bg-rose-600 shadow-rose-200' : 'bg-leaf-600 shadow-green-200 hover:bg-leaf-700'} disabled:bg-slate-300`}><>{listening ? <MicOff size={38} /> : <Mic size={38} />}</><span className="mt-1 text-xs font-bold">{listening ? 'ఆపండి' : 'మాట్లాడండి'}</span></button></div>
          {sessionId && <p className="mb-4 text-center text-xs text-slate-500">{supported ? 'మైక్ నొక్కి తెలుగులో మాట్లాడండి లేదా క్రింద టైప్ చేయండి.' : 'టెక్స్ట్ లేదా కీప్యాడ్ ఉపయోగించండి.'}</p>}
          <div className="flex gap-2"><input value={input} disabled={!sessionId || busy} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && sendMessage()} placeholder="మీ సమస్యను ఇక్కడ టైప్ చేయండి" className="min-w-0 flex-1 rounded-xl border border-slate-200 px-4 py-3 text-sm" /><button onClick={sendMessage} disabled={!sessionId || busy || !input.trim()} className="grid w-12 place-items-center rounded-xl bg-leaf-600 text-white disabled:bg-slate-300"><Send size={20} /></button></div>
          <div className="mt-4"><Keypad disabled={!sessionId || busy} onPick={(value) => setInput((current) => current ? `${current} ${value}` : value)} onDelete={() => setInput((current) => current.slice(0, -1))} onSend={sendMessage} language={language} /></div>
          {sessionId && <button onClick={endConversation} className="mx-auto mt-5 flex items-center gap-2 text-sm font-bold text-slate-500 hover:text-rose-700"><PhoneOff size={17} /> సెషన్ ముగించండి</button>}
          {caseId && <div className="mt-5 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-center"><div className="flex justify-center text-emerald-700"><CheckCircle2 /></div><p className="mt-2 text-sm font-bold text-emerald-900">కేసు నమోదు అయింది: {caseId}</p><p className="mt-1 text-xs text-emerald-800">డెమోలో నిపుణుల సమీక్ష అవసరం అని గుర్తించబడింది.</p><label className="mt-3 block rounded-xl border border-emerald-200 bg-white p-3 text-left text-xs font-bold text-emerald-900">పంట ఫోటో జోడించండి (ఐచ్ఛికం)<input type="file" accept="image/jpeg,image/png,image/webp" onChange={uploadPhoto} disabled={busy} className="mt-2 block w-full text-xs font-normal text-slate-600" /></label>{photoStatus && <p className="mt-2 text-xs font-medium text-emerald-800">{photoStatus}</p>}{!feedbackDone && <div className="mt-3"><p className="mb-2 text-sm font-bold text-slate-700">మీ పత్తి పంట పరిస్థితి ఇప్పుడు ఎలా ఉంది?</p><div className="grid grid-cols-3 gap-2"><button onClick={() => sendFeedback('IMPROVED')} disabled={busy} className="rounded-lg bg-white px-2 py-2 text-xs font-bold text-emerald-700">మెరుగుపడింది</button><button onClick={() => sendFeedback('UNCHANGED')} disabled={busy} className="rounded-lg bg-white px-2 py-2 text-xs font-bold text-amber-700">మార్పు లేదు</button><button onClick={() => sendFeedback('WORSENED')} disabled={busy} className="rounded-lg bg-white px-2 py-2 text-xs font-bold text-rose-700">దిగజారింది</button></div></div>}</div>}
        </section>
        <p className="mx-auto mt-5 max-w-lg text-center text-xs leading-5 text-slate-500">ఇది నల్గొండ జిల్లా పత్తి పైలట్ మాత్రమే. నిపుణుడి ధృవీకరణ లేకుండా పురుగుమందులు లేదా మోతాదులు సూచించబడవు.</p>
      </div>
    </main>
  ))
}
