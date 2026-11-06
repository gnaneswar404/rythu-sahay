import { useEffect, useRef, useState } from 'react'
import {
  ArrowLeft,
  CalendarDays,
  ClipboardList,
  CircleUserRound,
  Eye,
  EyeOff,
  FileText,
  Filter,
  Leaf,
  LogIn,
  RefreshCw,
  Search,
  UserCheck,
  X,
} from 'lucide-react'
import Brand from '../components/Brand'
import StatusPill from '../components/StatusPill'
import { expertApi, setExpertToken } from '../services/api'
import { translateTree } from '../i18n'

const demoCredentials = { email: 'demo.expert@example.com', password: 'demo-expert' }
const buildTimeGoogleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID?.trim()
const cards = [
  ['total_cases', 'మొత్తం కేసులు', ClipboardList, 'text-slate-700 bg-slate-100'],
  ['new_cases', 'కొత్త కేసులు', Leaf, 'text-sky-700 bg-sky-100'],
  ['escalated_cases', 'ఎస్కలేట్ చేసినవి', FileText, 'text-rose-700 bg-rose-100'],
  ['pending_followups', 'పెండింగ్ ఫాలో-అప్‌లు', CalendarDays, 'text-amber-700 bg-amber-100'],
]

function errorText(error, fallback) {
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const message = detail.find((item) => typeof item?.msg === 'string')?.msg
    if (message) return message
  }
  return fallback
}

function imageUrls(value) {
  try {
    const parsed = JSON.parse(value || '[]')
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function ProtectedPhoto({ caseId, url }) {
  const [objectUrl, setObjectUrl] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    let imageUrl = ''
    setObjectUrl('')
    setError('')
    const filename = url.split('/').pop()
    expertApi.casePhoto(caseId, filename)
      .then(({ data }) => {
        if (active) {
          imageUrl = URL.createObjectURL(data)
          setObjectUrl(imageUrl)
        }
      })
      .catch(() => {
        if (active) setError('ఫోటోను లోడ్ చేయలేకపోయాము.')
      })
    return () => {
      active = false
      if (imageUrl) URL.revokeObjectURL(imageUrl)
    }
  }, [caseId, url])

  if (error) return <p role="alert" className="rounded-lg bg-rose-50 p-2 text-xs text-rose-800">{error}</p>
  if (!objectUrl) return <p role="status" className="rounded-lg bg-slate-50 p-2 text-xs text-slate-500">ఫోటో లోడ్ అవుతోంది…</p>
  return (
    <a href={objectUrl} target="_blank" rel="noreferrer">
      <img src={objectUrl} alt="రైతు అప్‌లోడ్ చేసిన పంట ఫోటో" className="h-28 w-full rounded-lg object-cover" />
    </a>
  )
}

function Login({ onLoggedIn, onBack, language }) {
  const [form, setForm] = useState(demoCredentials)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [googleError, setGoogleError] = useState('')
  const [googleClientId, setGoogleClientId] = useState(buildTimeGoogleClientId)
  const [loadingGoogleConfig, setLoadingGoogleConfig] = useState(!buildTimeGoogleClientId)
  const googleButton = useRef(null)

  const completeSignIn = async (session) => {
    setExpertToken(session.access_token)
    try {
      const { data: profile } = await expertApi.me()
      onLoggedIn({
        token: session.access_token,
        expertId: session.expert_id,
        expertName: profile.name,
        profile,
      })
    } catch (requestError) {
      setExpertToken(null)
      throw requestError
    }
  }

  useEffect(() => {
    if (buildTimeGoogleClientId) return undefined

    let active = true
    expertApi.googleConfig()
      .then(({ data }) => {
        if (active) setGoogleClientId(data.client_id?.trim() || '')
      })
      .catch(() => {
        if (active) setGoogleError('Could not load Google sign-in configuration. Please refresh and try again.')
      })
      .finally(() => {
        if (active) setLoadingGoogleConfig(false)
      })

    return () => { active = false }
  }, [])

  const signInWithGoogle = async (credential) => {
    if (!credential) {
      setGoogleError('Google sign-in did not return a credential. Please try again.')
      return
    }
    setBusy(true)
    setGoogleError('')
    try {
      const { data } = await expertApi.googleLogin(credential)
      await completeSignIn(data)
    } catch (requestError) {
      setGoogleError(errorText(requestError, 'Google sign-in failed. Please try again.'))
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    if (!googleClientId) return undefined

    let cancelled = false
    const handleLoad = () => {
      if (cancelled) return
      if (!window.google?.accounts?.id || !googleButton.current) {
        setGoogleError('Google sign-in could not be loaded. Please refresh and try again.')
        return
      }

      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: (response) => { void signInWithGoogle(response?.credential) },
      })
      googleButton.current.replaceChildren()
      window.google.accounts.id.renderButton(googleButton.current, {
        theme: 'outline',
        size: 'large',
        text: 'continue_with',
        shape: 'rectangular',
        width: 360,
      })
    }
    const handleError = () => {
      if (!cancelled) setGoogleError('Google sign-in could not be loaded. Please refresh and try again.')
    }

    let script = document.querySelector('script[data-google-identity]')
    if (window.google?.accounts?.id) {
      handleLoad()
    } else if (script) {
      script.addEventListener('load', handleLoad, { once: true })
      script.addEventListener('error', handleError, { once: true })
    } else {
      script = document.createElement('script')
      script.src = 'https://accounts.google.com/gsi/client'
      script.async = true
      script.defer = true
      script.dataset.googleIdentity = 'true'
      script.addEventListener('load', handleLoad, { once: true })
      script.addEventListener('error', handleError, { once: true })
      document.head.appendChild(script)
    }

    return () => {
      cancelled = true
      script?.removeEventListener('load', handleLoad)
      script?.removeEventListener('error', handleError)
    }
  }, [googleClientId])

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const { data } = await expertApi.login(form)
      await completeSignIn(data)
    } catch (requestError) {
      setError(errorText(requestError, 'లాగిన్ విఫలమైంది. వివరాలను పరిశీలించండి.'))
    } finally {
      setBusy(false)
    }
  }

  return translateTree(language, (
    <main className="grid min-h-screen place-items-center bg-leaf-50 p-4">
      <section className="w-full max-w-md rounded-3xl bg-white p-7 shadow-soft">
        <div className="mb-8 flex items-center justify-between">
          <Brand compact language={language} />
          <button onClick={onBack} className="flex items-center gap-1 text-sm font-bold text-slate-500">
            <ArrowLeft size={16} /> రైతు పేజీ
          </button>
        </div>
        <p className="text-2xl font-extrabold text-slate-800">నిపుణుల డాష్‌బోర్డ్</p>
        <p className="mt-2 text-sm leading-6 text-slate-600">అధీకృత వ్యవసాయ నిపుణుల కోసం మాత్రమే.</p>
        <p className="mt-3 text-sm text-slate-700">Google ఖాతాతో కొనసాగడానికి Google బటన్‌ను ఎంచుకోండి. మీ Google పాస్‌వర్డ్‌ను ఈ పేజీలో నమోదు చేయవద్దు.</p>
        {loadingGoogleConfig ? (
          <p role="status" className="my-4 text-center text-sm text-slate-600">Loading Google sign-in…</p>
        ) : googleClientId ? (
          <>
            <div className="my-4 flex min-h-10 justify-center" ref={googleButton} />
            {googleError && <p role="alert" className="mb-4 rounded-xl bg-rose-50 p-3 text-sm text-rose-800">{googleError}</p>}
          </>
        ) : (
          <>
            <p role="status" className="my-4 rounded-xl bg-amber-50 p-3 text-sm text-amber-900">
              Google సైన్-ఇన్ ఇంకా సెటప్ కాలేదు. backend/.env లో GOOGLE_CLIENT_ID నమోదు చేసి, బ్యాకెండ్‌ను మళ్లీ ప్రారంభించండి.
            </p>
            {googleError && <p role="alert" className="mb-4 rounded-xl bg-rose-50 p-3 text-sm text-rose-800">{googleError}</p>}
          </>
        )}
        <div className="my-5 rounded-xl bg-amber-50 p-3 text-xs leading-5 text-amber-900">
          డెమో ఖాతా ముందే నింపబడింది. ఇది నిజమైన రైతు లేదా నిపుణుల డేటా కాదు.
        </div>
        <p className="mb-3 text-sm font-bold text-slate-700">డెమో / యాప్ ఖాతాతో సైన్ ఇన్</p>
        <form onSubmit={submit} className="space-y-4">
          <label className="block text-sm font-bold text-slate-700">
            ఇమెయిల్
            <input
              type="email"
              value={form.email}
              onChange={(event) => setForm({ ...form, email: event.target.value })}
              className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-3 font-normal"
            />
          </label>
          <label className="block text-sm font-bold text-slate-700">
            పాస్‌వర్డ్
            <div className="relative mt-1">
              <input
                type={showPassword ? 'text' : 'password'}
                value={form.password}
                onChange={(event) => setForm({ ...form, password: event.target.value })}
                autoComplete="current-password"
                className="w-full rounded-xl border border-slate-200 px-3 py-3 pr-12 font-normal"
              />
              <button
                type="button"
                onClick={() => setShowPassword((visible) => !visible)}
                className="absolute inset-y-0 right-0 flex w-12 items-center justify-center text-slate-500 hover:text-slate-800"
                aria-label={showPassword ? 'పాస్‌వర్డ్ దాచు' : 'పాస్‌వర్డ్ చూపించు'}
                title={showPassword ? 'పాస్‌వర్డ్ దాచు' : 'పాస్‌వర్డ్ చూపించు'}
              >
                {showPassword ? <EyeOff size={19} /> : <Eye size={19} />}
              </button>
            </div>
          </label>
          {error && <p className="rounded-xl bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
          <button
            disabled={busy}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-leaf-600 py-3 font-bold text-white hover:bg-leaf-700 disabled:bg-slate-300"
          >
            <LogIn size={18} />
            {busy ? 'లాగిన్ అవుతోంది…' : 'లాగిన్ చేయండి'}
          </button>
        </form>
      </section>
    </main>
  ))
}

function CasePanel({ selected, expertId, onUpdated, language }) {
  const [detail, setDetail] = useState(null)
  const [note, setNote] = useState('')
  const [followupDate, setFollowupDate] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let live = true
    if (!selected) {
      setDetail(null)
      return undefined
    }
    expertApi.caseDetail(selected.id)
      .then(({ data }) => live && setDetail(data))
      .catch((requestError) => live && setError(errorText(requestError, 'కేసు వివరాలు అందుబాటులో లేవు.')))
    return () => { live = false }
  }, [selected])

  if (!selected) {
    return translateTree(language, (
      <aside className="hidden rounded-2xl border border-slate-200 bg-white p-8 lg:block">
        <p className="text-center text-sm text-slate-500">వివరాలు చూడడానికి ఒక కేసును ఎంచుకోండి.</p>
      </aside>
    ))
  }

  const current = detail || selected
  const photos = imageUrls(current.image_urls)
  const perform = async (action) => {
    setBusy(true)
    setError('')
    try {
      await action()
      await onUpdated(selected.id)
      const { data } = await expertApi.caseDetail(selected.id)
      setDetail(data)
    } catch (requestError) {
      setError(errorText(requestError, 'మార్పు సేవ్ కాలేదు.'))
    } finally {
      setBusy(false)
    }
  }

  return translateTree(language, (
    <aside className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold text-slate-400">కేసు</p>
          <h2 className="text-xl font-extrabold text-slate-800">{current.id}</h2>
        </div>
        <StatusPill status={current.status} language={language} />
      </div>
      <div className="mt-4 rounded-xl bg-leaf-50 p-3 text-sm leading-6 text-slate-700">
        <p className="font-bold text-leaf-700">రైతు వివరాలు</p>
        <p>{current.farmer?.name || 'పేరు ఇంకా నమోదు కాలేదు'}</p>
        <p>{current.village || 'గ్రామం తెలియదు'} · {current.mandal || 'మండలం తెలియదు'}</p>
        <p className="text-xs text-slate-500">{current.district} · {current.crop}</p>
      </div>
      <div className="mt-4">
        <p className="text-xs font-bold uppercase tracking-wider text-slate-400">సమస్య</p>
        <p className="mt-1 text-sm leading-6 text-slate-700">{current.description}</p>
        {current.symptoms && <p className="mt-2 text-sm text-slate-600">లక్షణాలు: {current.symptoms}</p>}
      </div>
      <div className="mt-4">
        <p className="text-xs font-bold uppercase tracking-wider text-slate-400">AI సారాంశం</p>
        <p className="mt-1 text-sm leading-6 text-slate-700">{current.ai_summary || 'సారాంశం ఇంకా అందుబాటులో లేదు.'}</p>
      </div>
      {photos.length > 0 && (
        <div className="mt-4">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-400">పంట ఫోటోలు</p>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {photos.map((url) => <ProtectedPhoto key={url} caseId={current.id} url={url} />)}
          </div>
        </div>
      )}
      <div className="mt-5 grid grid-cols-2 gap-2">
        <button
          disabled={busy}
          onClick={() => perform(() => expertApi.assign(current.id, { expert_id: expertId }))}
          className="flex items-center justify-center gap-2 rounded-xl bg-leaf-600 py-2.5 text-sm font-bold text-white disabled:bg-slate-300"
        >
          <UserCheck size={16} /> నాకు కేటాయించు
        </button>
        <button
          disabled={busy}
          onClick={() => perform(() => expertApi.status(current.id, { status: 'UNDER_REVIEW' }))}
          className="rounded-xl border border-leaf-200 py-2.5 text-sm font-bold text-leaf-700 disabled:opacity-50"
        >
          సమీక్షలో ఉంది
        </button>
      </div>
      <div className="mt-4 rounded-xl border border-slate-200 p-3">
        <label className="text-sm font-bold text-slate-700">
          నిపుణుల గమనిక / ధృవీకరించిన చర్య
          <textarea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="ధృవీకరించిన సిఫార్సు లేదా గమనిక నమోదు చేయండి"
            className="mt-2 h-20 w-full resize-none rounded-lg border border-slate-200 p-2 text-sm font-normal"
          />
        </label>
        <button
          disabled={!note.trim() || busy}
          onClick={() => perform(async () => {
            await expertApi.note(current.id, { description: note, expert_approved: true })
            await expertApi.status(current.id, { status: 'GUIDANCE_PROVIDED', recommended_next_action: note })
            setNote('')
          })}
          className="mt-2 w-full rounded-lg bg-slate-800 py-2 text-sm font-bold text-white disabled:bg-slate-300"
        >
          గమనిక సేవ్ చేయండి
        </button>
      </div>
      <div className="mt-4 rounded-xl border border-slate-200 p-3">
        <label className="text-sm font-bold text-slate-700">
          ఫాలో-అప్ తేదీ
          <input
            type="date"
            value={followupDate}
            onChange={(event) => setFollowupDate(event.target.value)}
            className="mt-2 w-full rounded-lg border border-slate-200 p-2 font-normal"
          />
        </label>
        <button
          disabled={!followupDate || busy}
          onClick={() => perform(() => expertApi.followup(current.id, { scheduled_date: followupDate }))}
          className="mt-2 w-full rounded-lg bg-amber-500 py-2 text-sm font-bold text-white disabled:bg-slate-300"
        >
          ఫాలో-అప్ షెడ్యూల్ చేయండి
        </button>
      </div>
      {error && <p className="mt-3 rounded-lg bg-rose-50 p-2 text-xs text-rose-800">{error}</p>}
      <div className="mt-5">
        <p className="text-xs font-bold uppercase tracking-wider text-slate-400">చర్యల చరిత్ర</p>
        <div className="mt-2 space-y-2">
          {(current.actions || []).slice().reverse().map((action) => (
            <div key={action.id} className="rounded-lg bg-slate-50 p-2 text-xs text-slate-600">
              <b>{action.action_type}</b><br />{action.description}
            </div>
          ))}
        </div>
      </div>
    </aside>
  ))
}

function ProfileSetup({ auth, onCompleted, onLogout, language }) {
  const [form, setForm] = useState({
    name: auth.profile.name || '',
    phone_number: auth.profile.phone_number || '',
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const { data } = await expertApi.updateMe(form)
      onCompleted(data)
    } catch (requestError) {
      setError(errorText(requestError, 'మీ ప్రొఫైల్‌ను సేవ్ చేయలేకపోయాము. దయచేసి మళ్లీ ప్రయత్నించండి.'))
    } finally {
      setBusy(false)
    }
  }

  return translateTree(language, (
    <main className="grid min-h-screen place-items-center bg-leaf-50 p-4">
      <section className="w-full max-w-md rounded-3xl bg-white p-7 shadow-soft">
        <div className="mb-8 flex items-center justify-between">
          <Brand compact language={language} />
          <button onClick={onLogout} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-bold text-slate-600">లాగ్ అవుట్</button>
        </div>
        <p className="text-2xl font-extrabold text-slate-800">మీ ప్రొఫైల్‌ను పూర్తి చేయండి</p>
        <p className="mt-2 text-sm leading-6 text-slate-600">డాష్‌బోర్డ్‌కు వెళ్లే ముందు మీ ఖాతా వివరాలను నిర్ధారించండి.</p>
        <form onSubmit={submit} className="mt-6 space-y-4">
          <label className="block text-sm font-bold text-slate-700">
            పూర్తి పేరు
            <input
              required
              autoComplete="name"
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-3 font-normal"
            />
          </label>
          <label className="block text-sm font-bold text-slate-700">
            ఇమెయిల్ చిరునామా
            <input
              type="email"
              value={auth.profile.email}
              readOnly
              aria-readonly="true"
              className="mt-1 w-full cursor-not-allowed rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 font-normal text-slate-500"
            />
          </label>
          <label className="block text-sm font-bold text-slate-700">
            ఫోన్ నంబర్
            <input
              required
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              value={form.phone_number}
              onChange={(event) => setForm({ ...form, phone_number: event.target.value })}
              placeholder="ఉదా. +91 98765 43210"
              className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-3 font-normal"
            />
          </label>
          <p className="rounded-xl bg-slate-50 p-3 text-xs leading-5 text-slate-600">మీ సంప్రదింపు వివరాలు మీ ప్రొఫైల్‌లో మాత్రమే కనిపిస్తాయి.</p>
          {error && <p role="alert" className="rounded-xl bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
          <button
            disabled={busy}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-leaf-600 py-3 font-bold text-white hover:bg-leaf-700 disabled:bg-slate-300"
          >
            {busy ? 'ప్రొఫైల్ సేవ్ అవుతోంది…' : 'ప్రొఫైల్‌ను సేవ్ చేసి డాష్‌బోర్డ్‌కు వెళ్లండి'}
          </button>
        </form>
      </section>
    </main>
  ))
}

function Dashboard({ auth, onLogout, onBack, language }) {
  const [summary, setSummary] = useState(null)
  const [cases, setCases] = useState([])
  const [selected, setSelected] = useState(null)
  const [filters, setFilters] = useState({ search: '', case_status: '' })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [profile, setProfile] = useState(auth.profile || null)
  const [profileOpen, setProfileOpen] = useState(false)
  const [profileLoading, setProfileLoading] = useState(false)
  const [profileError, setProfileError] = useState('')

  const load = async (keepSelection = true) => {
    setLoading(true)
    setError('')
    try {
      const query = Object.fromEntries(Object.entries(filters).filter(([, value]) => value))
      const [summaryResponse, casesResponse] = await Promise.all([
        expertApi.summary(),
        expertApi.cases(query),
      ])
      setSummary(summaryResponse.data)
      setCases(casesResponse.data)
      if (!keepSelection) setSelected(null)
      else if (selected) setSelected(casesResponse.data.find((item) => item.id === selected.id) || null)
    } catch (requestError) {
      setError(errorText(requestError, 'డేటా లోడ్ కాలేదు. మళ్లీ ప్రయత్నించండి.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(false) }, [])

  const toggleProfile = async () => {
    if (profileOpen) {
      setProfileOpen(false)
      return
    }

    setProfileOpen(true)
    if (profile || profileLoading) return

    setProfileLoading(true)
    setProfileError('')
    try {
      const { data } = await expertApi.me()
      setProfile(data)
    } catch (requestError) {
      setProfileError(errorText(requestError, 'ప్రొఫైల్ వివరాలు లోడ్ కాలేదు.'))
    } finally {
      setProfileLoading(false)
    }
  }

  const reloadAndSelect = async (id) => {
    await load(true)
    const { data } = await expertApi.caseDetail(id)
    setSelected(data)
  }

  return translateTree(language, (
    <main className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white px-4 py-3 sm:px-6">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <Brand compact language={language} />
          <div className="flex items-center gap-3">
            <span className="hidden text-sm font-semibold text-slate-600 sm:inline">{auth.expertName}</span>
            <div className="relative">
              <button
                type="button"
                onClick={toggleProfile}
                aria-expanded={profileOpen}
                aria-controls="expert-profile"
                className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50"
              >
                <CircleUserRound size={16} /> నా ప్రొఫైల్
              </button>
              {profileOpen && (
                <section
                  id="expert-profile"
                  role="dialog"
                  aria-label="ఖాతా వివరాలు"
                  className="absolute right-0 top-11 z-20 w-80 rounded-2xl border border-slate-200 bg-white p-4 shadow-lg"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="grid h-10 w-10 place-items-center rounded-full bg-leaf-100 font-extrabold text-leaf-700">
                        {(profile?.name || auth.expertName || '?').trim().charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <h2 className="font-extrabold text-slate-800">ఖాతా వివరాలు</h2>
                        <p className="text-xs text-slate-500">మీ సైన్ ఇన్ చేసిన ప్రొఫైల్</p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setProfileOpen(false)}
                      aria-label="మూసివేయండి"
                      title="మూసివేయండి"
                      className="rounded-md p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                    >
                      <X size={18} />
                    </button>
                  </div>
                  {profileLoading ? (
                    <p className="py-6 text-center text-sm text-slate-500">ప్రొఫైల్ లోడ్ అవుతోంది…</p>
                  ) : profile ? (
                    <dl className="mt-4 space-y-3 text-sm">
                      <div>
                        <dt className="text-xs font-bold uppercase tracking-wide text-slate-400">పేరు</dt>
                        <dd className="mt-0.5 break-words font-semibold text-slate-700">{profile.name}</dd>
                      </div>
                      <div>
                        <dt className="text-xs font-bold uppercase tracking-wide text-slate-400">ఇమెయిల్ చిరునామా</dt>
                        <dd className="mt-0.5 break-all text-slate-700">{profile.email}</dd>
                      </div>
                      <div>
                        <dt className="text-xs font-bold uppercase tracking-wide text-slate-400">ఫోన్ నంబర్</dt>
                        <dd className="mt-0.5 break-words text-slate-700">{profile.phone_number || '–'}</dd>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <dt className="text-xs font-bold uppercase tracking-wide text-slate-400">ఖాతా ID</dt>
                          <dd className="mt-0.5 font-semibold text-slate-700">{profile.id}</dd>
                        </div>
                        <div>
                          <dt className="text-xs font-bold uppercase tracking-wide text-slate-400">పాత్ర</dt>
                          <dd className="mt-0.5 break-words text-slate-700">{profile.role}</dd>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <dt className="text-xs font-bold uppercase tracking-wide text-slate-400">ఖాతా రకం</dt>
                          <dd className="mt-0.5 text-slate-700">{profile.is_demo ? 'డెమో ఖాతా' : 'ధృవీకరించిన నిపుణుల ఖాతా'}</dd>
                        </div>
                        <div>
                          <dt className="text-xs font-bold uppercase tracking-wide text-slate-400">సృష్టించిన తేదీ</dt>
                          <dd className="mt-0.5 text-slate-700">{new Intl.DateTimeFormat(language === 'en' ? 'en-IN' : 'te-IN', { dateStyle: 'medium' }).format(new Date(profile.created_at))}</dd>
                        </div>
                      </div>
                    </dl>
                  ) : (
                    <p className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{profileError || 'ప్రొఫైల్ వివరాలు లోడ్ కాలేదు.'}</p>
                  )}
                </section>
              )}
            </div>
            <button onClick={onBack} className="text-xs font-bold text-slate-500">రైతు వీక్షణ</button>
            <button onClick={onLogout} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-bold text-slate-600">లాగ్ అవుట్</button>
          </div>
        </div>
      </header>
      <div className="mx-auto max-w-7xl p-4 sm:p-6">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-2xl font-extrabold text-slate-800">నిపుణుల డాష్‌బోర్డ్</p>
            <p className="mt-1 text-sm text-slate-500">నల్గొండ పత్తి కేసుల సమస్య పరిష్కార పర్యవేక్షణ</p>
          </div>
          <button onClick={() => load(true)} className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-bold text-slate-600">
            <RefreshCw size={16} /> రిఫ్రెష్
          </button>
        </div>
        <div className="mb-5 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
          {summary?.demo_data_notice || 'సింథటిక్ డెమో డేటా మాత్రమే.'}
        </div>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {cards.map(([key, label, Icon, color]) => (
            <div key={key} className="rounded-2xl bg-white p-4 shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-bold text-slate-500">{label}</p>
                  <p className="mt-2 text-3xl font-extrabold text-slate-800">{summary?.[key] ?? '–'}</p>
                </div>
                <div className={`rounded-xl p-3 ${color}`}><Icon size={21} /></div>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-6 grid gap-5 lg:grid-cols-[minmax(0,1fr)_380px]">
          <section className="min-w-0 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <form onSubmit={(event) => { event.preventDefault(); load(false) }} className="mb-4 flex flex-col gap-2 sm:flex-row">
              <div className="flex flex-1 items-center gap-2 rounded-xl border border-slate-200 px-3">
                <Search size={18} className="text-slate-400" />
                <input
                  value={filters.search}
                  onChange={(event) => setFilters({ ...filters, search: event.target.value })}
                  placeholder="కేసు ID లేదా సమస్య వెతకండి"
                  className="w-full py-3 text-sm outline-none"
                />
              </div>
              <select
                value={filters.case_status}
                onChange={(event) => setFilters({ ...filters, case_status: event.target.value })}
                className="rounded-xl border border-slate-200 px-3 py-3 text-sm"
              >
                <option value="">అన్ని స్థితులు</option>
                {['NEW', 'UNDER_REVIEW', 'ASSIGNED', 'GUIDANCE_PROVIDED', 'FOLLOW_UP_PENDING', 'RESOLVED', 'ESCALATED'].map((status) => (
                  <option key={status} value={status}>{status}</option>
                ))}
              </select>
              <button className="flex items-center justify-center gap-2 rounded-xl bg-leaf-600 px-4 py-3 text-sm font-bold text-white">
                <Filter size={16} /> ఫిల్టర్
              </button>
            </form>
            {error && <p className="mb-4 rounded-xl bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
            <div className="overflow-x-auto">
              <table className="w-full min-w-[650px] text-left">
                <thead className="border-y border-slate-100 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="p-3">కేసు</th>
                    <th className="p-3">ప్రాంతం</th>
                    <th className="p-3">తీవ్రత</th>
                    <th className="p-3">స్థితి</th>
                    <th className="p-3"></th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr><td colSpan="5" className="p-8 text-center text-sm text-slate-500">లోడ్ అవుతోంది…</td></tr>
                  ) : cases.length ? cases.map((item) => (
                    <tr key={item.id} className="border-b border-slate-100 hover:bg-leaf-50">
                      <td className="p-3">
                        <p className="font-bold text-slate-800">{item.id}</p>
                        <p className="max-w-52 truncate text-xs text-slate-500">{item.problem_category || item.description}</p>
                      </td>
                      <td className="p-3 text-sm text-slate-600">{item.village || '–'}<br /><span className="text-xs">{item.mandal || ''}</span></td>
                      <td className="p-3"><span className={`text-xs font-bold ${item.severity === 'HIGH' || item.severity === 'CRITICAL' ? 'text-rose-700' : 'text-amber-700'}`}>{item.severity}</span></td>
                      <td className="p-3"><StatusPill status={item.status} language={language} /></td>
                      <td className="p-3">
                        <button onClick={() => setSelected(item)} className="rounded-lg border border-leaf-200 px-3 py-2 text-xs font-bold text-leaf-700">చూడండి</button>
                      </td>
                    </tr>
                  )) : (
                    <tr><td colSpan="5" className="p-8 text-center text-sm text-slate-500">కేసులు కనబడలేదు.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
          <CasePanel selected={selected} expertId={auth.expertId} onUpdated={reloadAndSelect} language={language} />
        </div>
      </div>
    </main>
  ))
}

export default function ExpertDashboard({ onBack, language }) {
  const [auth, setAuth] = useState(null)
  const logout = () => {
    setExpertToken(null)
    setAuth(null)
  }
  const completeProfile = (profile) => {
    setAuth((current) => current && {
      ...current,
      expertName: profile.name,
      profile,
    })
  }
  return auth
    ? auth.profile?.phone_number
      ? <Dashboard auth={auth} onLogout={logout} onBack={onBack} language={language} />
      : <ProfileSetup auth={auth} onCompleted={completeProfile} onLogout={logout} language={language} />
    : <Login onLoggedIn={setAuth} onBack={onBack} language={language} />
}
