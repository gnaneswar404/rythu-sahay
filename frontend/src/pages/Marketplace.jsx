import { useEffect, useState } from 'react'
import { ArrowLeft, CalendarDays, Check, LocateFixed, LogOut, MapPin, Phone, Plus, Users } from 'lucide-react'
import Brand from '../components/Brand'
import { marketApi, marketAuthApi, setMarketToken } from '../services/api'
import { translateTree } from '../i18n'

function messageFrom(error, fallback) {
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const message = detail.find((item) => typeof item?.msg === 'string')?.msg
    if (message) return message
  }
  return fallback
}

function UsernameLogin({ accountType, onBack, onLogin, language }) {
  const isFarmer = accountType === 'farmer'
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [phone, setPhone] = useState('')
  const [creating, setCreating] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const request = {
        account_type: accountType,
        username,
        password,
        ...(creating && phone.trim() ? { phone: phone.trim() } : {}),
      }
      const { data } = creating
        ? await marketAuthApi.register(request)
        : await marketAuthApi.login(request)
      setMarketToken(data.access_token, data)
      onLogin(data)
    } catch (requestError) {
      setError(messageFrom(requestError, creating
        ? 'ఖాతా సృష్టించలేకపోయాము. వివరాలను తనిఖీ చేసి మళ్లీ ప్రయత్నించండి.'
        : 'వినియోగదారు పేరు లేదా పాస్‌వర్డ్ తప్పు. మళ్లీ ప్రయత్నించండి.'))
    } finally {
      setBusy(false)
    }
  }

  return translateTree(language, (
    <main className="grid min-h-[calc(100vh-44px)] place-items-center bg-leaf-50 p-4">
      <section className="w-full max-w-md rounded-3xl bg-white p-6 shadow-soft sm:p-8">
        <div className="mb-7 flex items-center justify-between">
          <Brand compact language={language} />
          <button type="button" onClick={onBack} className="flex items-center gap-1 text-sm font-bold text-slate-500"><ArrowLeft size={16} /> వెనుకకు</button>
        </div>
        <h1 className="text-2xl font-extrabold text-slate-800">{isFarmer ? 'రైతు ఖాతా' : 'కూలీ ఖాతా'}</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">వినియోగదారు పేరు మరియు పాస్‌వర్డ్‌తో మీ ఖాతాను సృష్టించండి లేదా మళ్లీ లాగిన్ చేయండి.</p>
        <div className="mt-5 grid grid-cols-2 rounded-xl bg-slate-100 p-1" role="group" aria-label="ఖాతా విధానం">
          <button type="button" onClick={() => { setCreating(false); setError('') }} aria-pressed={!creating} className={`rounded-lg py-2 text-sm font-bold ${!creating ? 'bg-white text-leaf-700 shadow-sm' : 'text-slate-600'}`}>లాగిన్</button>
          <button type="button" onClick={() => { setCreating(true); setError('') }} aria-pressed={creating} className={`rounded-lg py-2 text-sm font-bold ${creating ? 'bg-white text-leaf-700 shadow-sm' : 'text-slate-600'}`}>కొత్త ఖాతా</button>
        </div>
        <form onSubmit={submit} className="mt-5 space-y-4">
          <label className="block text-sm font-bold text-slate-700">వినియోగదారు పేరు<input required minLength="3" maxLength="32" pattern="[A-Za-z0-9._-]+" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-3 font-normal" /></label>
          <label className="block text-sm font-bold text-slate-700">పాస్‌వర్డ్<input required type="password" minLength="8" maxLength="72" autoComplete={creating ? 'new-password' : 'current-password'} value={password} onChange={(event) => setPassword(event.target.value)} className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-3 font-normal" /><span className="mt-1 block text-xs font-normal text-slate-500">కనీసం 8 అక్షరాలు</span></label>
          {creating && <label className="block text-sm font-bold text-slate-700">ఫోన్ నంబర్ (ఐచ్ఛికం)<input type="tel" inputMode="tel" autoComplete="tel" maxLength="16" value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="+91 98765 43210" className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-3 font-normal" /><span className="mt-1 block text-xs font-normal text-slate-500">లాగిన్ కోసం అవసరం లేదు; మార్కెట్‌ప్లేస్ సంప్రదింపుల కోసం మాత్రమే.</span></label>}
          {error && <p role="alert" className="rounded-xl bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
          <button disabled={busy} className="w-full rounded-xl bg-leaf-600 py-3 font-bold text-white disabled:bg-slate-300">{busy ? 'దయచేసి వేచి ఉండండి…' : creating ? 'ఖాతా సృష్టించండి' : 'లాగిన్'}</button>
        </form>
      </section>
    </main>
  ))
}

function MarketplaceDashboard({ account, accountType, onLogout, onSessionExpired, language }) {
  const isFarmer = accountType === 'farmer'
  const [tab, setTab] = useState(isFarmer ? 'cases' : 'jobs')
  const [profile, setProfile] = useState(null)
  const [cases, setCases] = useState([])
  const [jobs, setJobs] = useState([])
  const [bookings, setBookings] = useState([])
  const [applications, setApplications] = useState([])
  const [teams, setTeams] = useState([])
  const [nearbyWorkers, setNearbyWorkers] = useState([])
  const [appsByJob, setAppsByJob] = useState({})
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [profileForm, setProfileForm] = useState({
    name: account.name || '',
    village: '',
    mandal: '',
    latitude: '',
    longitude: '',
    preferred_language: language,
    skills: '',
    daily_wage: '',
    is_available: true,
  })
  const [jobForm, setJobForm] = useState({ title: '', description: '', village: '', mandal: '', work_date: '', required_workers: 1, daily_wage: '', latitude: '', longitude: '' })
  const [teamName, setTeamName] = useState('')
  const [teamPhones, setTeamPhones] = useState({})
  const [jobWages, setJobWages] = useState({})
  const [applicationWages, setApplicationWages] = useState({})
  const [selectedJobsByWorker, setSelectedJobsByWorker] = useState({})

  const load = async () => {
    setError('')
    setBusy(true)
    try {
      if (isFarmer) {
        const [profileResponse, caseResponse, jobsResponse, bookingsResponse] = await Promise.all([
          marketApi.farmerProfile(), marketApi.farmerCases(), marketApi.myJobs(), marketApi.farmerBookings(),
        ])
        setProfile(profileResponse.data)
        setProfileForm((current) => ({ ...current, ...profileResponse.data, latitude: profileResponse.data.latitude ?? '', longitude: profileResponse.data.longitude ?? '' }))
        setCases(caseResponse.data)
        setJobs(jobsResponse.data)
        setBookings(bookingsResponse.data)
        if (profileResponse.data.latitude !== null && profileResponse.data.latitude !== undefined && profileResponse.data.longitude !== null && profileResponse.data.longitude !== undefined) {
          const workerResponse = await marketApi.nearbyWorkers(50)
          setNearbyWorkers(workerResponse.data)
        } else {
          setNearbyWorkers([])
        }
      } else {
        const [profileResponse, teamsResponse, applicationsResponse, bookingsResponse] = await Promise.all([
          marketApi.workerProfile(), marketApi.myTeams(), marketApi.myApplications(), marketApi.workerBookings(),
        ])
        const worker = profileResponse.data
        setProfile(worker)
        setProfileForm((current) => ({ ...current, ...worker, latitude: worker.latitude ?? '', longitude: worker.longitude ?? '', daily_wage: worker.daily_wage ?? '' }))
        setTeams(teamsResponse.data)
        setApplications(applicationsResponse.data)
        setBookings(bookingsResponse.data)
        if (worker.latitude !== null && worker.latitude !== undefined && worker.longitude !== null && worker.longitude !== undefined) {
          const jobsResponse = await marketApi.nearbyJobs(50)
          setJobs(jobsResponse.data)
        } else {
          setJobs([])
        }
      }
    } catch (requestError) {
      if (requestError.response?.status === 401) {
        onSessionExpired()
        return
      }
      setError(messageFrom(requestError, 'సమాచారం లోడ్ కాలేదు. మళ్లీ ప్రయత్నించండి.'))
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => { void load() }, [accountType])

  const run = async (action, successMessage = 'మార్పు సేవ్ అయింది.') => {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await action()
      setNotice(successMessage)
      await load()
    } catch (requestError) {
      setError(messageFrom(requestError, 'చర్యను పూర్తి చేయలేకపోయాము. మళ్లీ ప్రయత్నించండి.'))
    } finally {
      setBusy(false)
    }
  }

  const saveProfile = (event) => {
    event.preventDefault()
    const body = {
      name: profileForm.name,
      village: profileForm.village || null,
      mandal: profileForm.mandal || null,
      latitude: profileForm.latitude === '' ? null : Number(profileForm.latitude),
      longitude: profileForm.longitude === '' ? null : Number(profileForm.longitude),
    }
    if (isFarmer) body.preferred_language = profileForm.preferred_language || language
    else {
      body.skills = profileForm.skills || ''
      body.daily_wage = profileForm.daily_wage === '' ? null : Number(profileForm.daily_wage)
      body.is_available = Boolean(profileForm.is_available)
    }
    void run(() => isFarmer ? marketApi.updateFarmerProfile(body) : marketApi.updateWorkerProfile(body), 'ప్రొఫైల్ సేవ్ అయింది.')
  }

  const locate = () => {
    if (!navigator.geolocation) {
      setError('ఈ పరికరంలో స్థానం గుర్తించడం అందుబాటులో లేదు.')
      return
    }
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => setProfileForm((current) => ({ ...current, latitude: String(coords.latitude), longitude: String(coords.longitude) })),
      () => setError('స్థాన అనుమతి లభించలేదు. అక్షాంశం, రేఖాంశాన్ని చేతితో నమోదు చేయండి.'),
      { enableHighAccuracy: false, timeout: 10000 },
    )
  }

  const submitJob = (event) => {
    event.preventDefault()
    const body = {
      ...jobForm,
      required_workers: Number(jobForm.required_workers),
      daily_wage: Number(jobForm.daily_wage),
      latitude: jobForm.latitude === '' ? null : Number(jobForm.latitude),
      longitude: jobForm.longitude === '' ? null : Number(jobForm.longitude),
    }
    void run(async () => {
      await marketApi.createJob(body)
      setJobForm((current) => ({ ...current, title: '', description: '', work_date: '', daily_wage: '' }))
      setTab('jobs')
    }, 'పని వివరాలు ప్రచురించబడ్డాయి.')
  }

  const loadApplications = async (jobId) => {
    setError('')
    try {
      const { data } = await marketApi.jobApplications(jobId)
      setAppsByJob((current) => ({ ...current, [jobId]: data }))
    } catch (requestError) {
      setError(messageFrom(requestError, 'దరఖాస్తులు లోడ్ కాలేదు.'))
    }
  }

  const nav = isFarmer
    ? [['cases', 'నా పంట కేసులు'], ['jobs', 'నా పనులు'], ['workers', 'దగ్గరలో కూలీలు'], ['post', 'పని నమోదు'], ['bookings', 'బుకింగ్‌లు'], ['profile', 'ప్రొఫైల్']]
    : [['jobs', 'దగ్గరలో పనులు'], ['applications', 'నా దరఖాస్తులు'], ['teams', 'నా బృందం'], ['bookings', 'బుకింగ్‌లు'], ['profile', 'ప్రొఫైల్']]
  const availableJobs = isFarmer
    ? jobs.filter((job) => job.status === 'OPEN' && job.work_date >= new Date().toISOString().slice(0, 10))
    : []

  const statusLabel = (value) => ({
    NEW: 'కొత్తది', INFORMATION_REQUIRED: 'వివరాలు కావాలి', UNDER_REVIEW: 'పరిశీలనలో', ASSIGNED: 'కేటాయించబడింది',
    GUIDANCE_PROVIDED: 'సలహా ఇచ్చారు', FOLLOW_UP_PENDING: 'తదుపరి సమాచారం పెండింగ్', RESOLVED: 'పరిష్కరించబడింది',
    ESCALATED: 'నిపుణుడికి పంపబడింది', OPEN: 'తెరిచి ఉంది', FILLED: 'కూలీలు దొరికారు',
    NEGOTIATING: 'వేతన చర్చ', ACCEPTED: 'అంగీకరించబడింది', PENDING: 'నిర్ధారణ పెండింగ్',
    CONFIRMED: 'నిర్ధారించబడింది', CANCELLED: 'రద్దు చేయబడింది',
  }[value] || value)

  const field = (label, key, props = {}) => (
    <label key={key} className="block text-sm font-bold text-slate-700">{label}
      <input {...props} value={profileForm[key] ?? ''} onChange={(event) => setProfileForm({ ...profileForm, [key]: event.target.type === 'checkbox' ? event.target.checked : event.target.value })} className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" />
    </label>
  )

  return translateTree(language, (
    <main className="min-h-[calc(100vh-44px)] bg-slate-50">
      <header className="border-b border-slate-200 bg-white px-4 py-3">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3">
          <Brand compact language={language} />
          <div className="flex items-center gap-2 text-right">
            <span className="hidden text-sm font-semibold text-slate-600 sm:inline">{profile?.name || account.name || profile?.phone}</span>
            <button type="button" onClick={onLogout} className="flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-2 text-xs font-bold text-slate-600"><LogOut size={15} /> లాగ్ అవుట్</button>
          </div>
        </div>
      </header>
      <div className="mx-auto max-w-6xl px-3 py-5 sm:px-6 sm:py-7">
        <h1 className="mb-1 text-2xl font-extrabold text-slate-800">{isFarmer ? 'రైతు డాష్‌బోర్డ్' : 'కూలీ డాష్‌బోర్డ్'}</h1>
        <p className="mb-5 text-sm text-slate-600">{isFarmer ? 'మీ పంట కేసులు, పనులు, బుకింగ్‌లను ఒకేచోట నిర్వహించండి.' : 'మీకు సరిపోయే దగ్గరి పనులు, వేతనాలు, బుకింగ్‌లను చూడండి.'}</p>
        <nav className="mb-5 flex gap-2 overflow-x-auto pb-2" aria-label="Dashboard sections">
          {nav.map(([key, label]) => <button key={key} type="button" onClick={() => setTab(key)} aria-current={tab === key ? 'page' : undefined} className={`shrink-0 rounded-xl px-3 py-2 text-sm font-bold ${tab === key ? 'bg-leaf-600 text-white' : 'bg-white text-slate-600'}`}>{label}</button>)}
          <button type="button" onClick={() => void load()} className="shrink-0 rounded-xl bg-white px-3 py-2 text-sm font-bold text-slate-600">రిఫ్రెష్</button>
        </nav>
        {error && <p role="alert" className="mb-4 rounded-xl bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
        {notice && <p role="status" className="mb-4 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</p>}
        {busy && <p role="status" className="mb-3 text-sm font-medium text-leaf-700">లోడ్ అవుతోంది…</p>}

        {tab === 'cases' && isFarmer && <section className="space-y-3">
          <h2 className="text-lg font-bold text-slate-800">మీ పంట సహాయ కేసులు</h2>
          {!cases.length && <p className="rounded-2xl bg-white p-5 text-sm text-slate-600">మీ ఖాతాతో నమోదు చేసిన కేసులు ఇంకా లేవు. రైతు సహాయకుడి ద్వారా కొత్త సమస్యను నమోదు చేయండి.</p>}
          {cases.map((item) => <article key={item.id} className="rounded-2xl bg-white p-4 shadow-sm sm:p-5"><div className="flex flex-wrap items-start justify-between gap-2"><h3 className="font-bold text-slate-800">{item.id} · {item.problem_category || 'పంట సమస్య'}</h3><span className="rounded-full bg-leaf-50 px-3 py-1 text-xs font-bold text-leaf-800">{statusLabel(item.status)}</span></div><p className="mt-2 text-sm leading-6 text-slate-600">{item.description}</p><p className="mt-2 text-xs text-slate-500">{item.village || 'గ్రామం నమోదు కాలేదు'} · {new Date(item.created_at).toLocaleDateString(language === 'en' ? 'en-IN' : 'te-IN')}</p>{item.recommended_next_action && <p className="mt-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">{item.recommended_next_action}</p>}</article>)}
        </section>}

        {tab === 'workers' && isFarmer && <section className="space-y-3">
          <h2 className="text-lg font-bold text-slate-800">మీ దగ్గరలో అందుబాటులో ఉన్న కూలీలు</h2>
          {!profile?.latitude && <p className="rounded-2xl bg-white p-5 text-sm text-slate-600">కూలీలను సరిపోల్చడానికి ముందుగా ప్రొఫైల్‌లో మీ స్థానం నమోదు చేయండి.</p>}
          {profile?.latitude && !nearbyWorkers.length && <p className="rounded-2xl bg-white p-5 text-sm text-slate-600">50 కి.మీ పరిధిలో అందుబాటులో ఉన్న కూలీలు లేరు.</p>}
          {nearbyWorkers.map((worker) => <article key={worker.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-white p-4 shadow-sm"><div><h3 className="font-bold text-slate-800">{worker.name}</h3><p className="mt-1 text-sm text-slate-600">{worker.village || 'గ్రామం నమోదు కాలేదు'} · {worker.skills || 'నైపుణ్యాలు నమోదు కాలేదు'}</p></div><div className="text-right text-sm"><p className="font-bold text-leaf-700">{worker.distance_km} కి.మీ</p><p className="text-slate-600">{worker.daily_wage ? `₹${worker.daily_wage}/రోజు` : 'వేతనం పేర్కొనలేదు'}</p></div><div className="flex w-full flex-wrap gap-2 sm:w-auto">{availableJobs.length ? <><select aria-label={`${worker.name} కోసం పని ఎంచుకోండి`} value={selectedJobsByWorker[worker.id] ?? availableJobs[0].id} onChange={(event) => setSelectedJobsByWorker({ ...selectedJobsByWorker, [worker.id]: Number(event.target.value) })} className="min-w-0 flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm sm:flex-none"><option value="" disabled>పని ఎంచుకోండి</option>{availableJobs.map((job) => <option key={job.id} value={job.id}>{job.title} · {job.work_date} · ₹{job.daily_wage}/రోజు</option>)}</select><button type="button" disabled={busy} onClick={() => void run(() => marketApi.bookWorker(selectedJobsByWorker[worker.id] ?? availableJobs[0].id, worker.id), 'బుకింగ్ అభ్యర్థన పంపబడింది. కూలీ ధృవీకరించిన తర్వాత బుకింగ్ ఖరారవుతుంది.')} className="rounded-lg bg-leaf-600 px-3 py-2 text-sm font-bold text-white disabled:bg-slate-300">కూలీని బుక్ చేయండి</button></> : <button type="button" onClick={() => setTab('post')} className="rounded-lg border border-leaf-300 px-3 py-2 text-sm font-bold text-leaf-700">ముందుగా పని నమోదు చేయండి</button>}</div></article>)}
          <p className="text-xs text-slate-500">కూలీల ఫోన్ నంబర్లు గోప్యంగా ఉంటాయి; నిర్ధారించిన బుకింగ్‌లో మాత్రమే సంప్రదింపు లభిస్తుంది.</p>
        </section>}

        {tab === 'post' && isFarmer && <form onSubmit={submitJob} className="grid gap-4 rounded-2xl bg-white p-4 shadow-sm sm:grid-cols-2 sm:p-6">
          <h2 className="text-lg font-bold text-slate-800 sm:col-span-2">వ్యవసాయ పనిని నమోదు చేయండి</h2>
          <label className="block text-sm font-bold text-slate-700">పని పేరు<input required minLength="3" maxLength="160" value={jobForm.title} onChange={(event) => setJobForm({ ...jobForm, title: event.target.value })} className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" /></label>
          <label className="block text-sm font-bold text-slate-700">పని తేదీ<input required type="date" min={new Date().toISOString().slice(0, 10)} value={jobForm.work_date} onChange={(event) => setJobForm({ ...jobForm, work_date: event.target.value })} className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" /></label>
          <label className="block text-sm font-bold text-slate-700">గ్రామం<input required value={jobForm.village} onChange={(event) => setJobForm({ ...jobForm, village: event.target.value })} className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" /></label>
          <label className="block text-sm font-bold text-slate-700">మండలం<input required value={jobForm.mandal} onChange={(event) => setJobForm({ ...jobForm, mandal: event.target.value })} className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" /></label>
          <label className="block text-sm font-bold text-slate-700">రోజు వేతనం (రూ.)<input required type="number" min="1" max="100000" value={jobForm.daily_wage} onChange={(event) => setJobForm({ ...jobForm, daily_wage: event.target.value })} className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" /></label>
          <label className="block text-sm font-bold text-slate-700">కావలసిన కూలీలు<input required type="number" min="1" max="100" value={jobForm.required_workers} onChange={(event) => setJobForm({ ...jobForm, required_workers: event.target.value })} className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" /></label>
          <label className="block text-sm font-bold text-slate-700 sm:col-span-2">పని వివరాలు<textarea maxLength="2000" value={jobForm.description} onChange={(event) => setJobForm({ ...jobForm, description: event.target.value })} className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" rows="3" /></label>
          <div className="flex items-center gap-2 sm:col-span-2"><button type="button" onClick={() => navigator.geolocation?.getCurrentPosition(({ coords }) => setJobForm((current) => ({ ...current, latitude: String(coords.latitude), longitude: String(coords.longitude) })), () => setError('స్థానం పొందలేకపోయాము.'))} className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-bold"><LocateFixed size={16} /> స్థానం జోడించండి</button><span className="text-xs text-slate-500">{jobForm.latitude ? 'స్థానం జోడించబడింది' : 'స్థానం లేకపోతే దగ్గరి మ్యాచ్‌లు కనిపించవు'}</span></div>
          <button disabled={busy} className="rounded-xl bg-leaf-600 py-3 font-bold text-white disabled:bg-slate-300 sm:col-span-2">పనిని ప్రచురించండి</button>
        </form>}

        {tab === 'jobs' && <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-lg font-bold text-slate-800">{isFarmer ? 'మీరు నమోదు చేసిన పనులు' : 'మీ దగ్గరలో ఉన్న పనులు'}</h2>{isFarmer && <button onClick={() => setTab('post')} className="flex items-center gap-1 rounded-lg bg-leaf-600 px-3 py-2 text-sm font-bold text-white"><Plus size={16} /> కొత్త పని</button>}</div>
          {!jobs.length && <p className="rounded-2xl bg-white p-5 text-sm text-slate-600">{!isFarmer && !profile?.latitude ? 'దగ్గరి పనులను చూడటానికి ప్రొఫైల్‌లో మీ స్థానం నమోదు చేయండి.' : 'పనులు ఏవీ లేవు.'}</p>}
          {jobs.map((job) => <article key={job.id} className="rounded-2xl bg-white p-4 shadow-sm sm:p-5"><div className="flex flex-wrap justify-between gap-2"><h3 className="font-bold text-slate-800">{job.title}</h3><span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold">{statusLabel(job.status)}</span></div><p className="mt-1 text-sm text-slate-600">{job.description}</p><p className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500"><span className="flex items-center gap-1"><MapPin size={13} />{job.village}, {job.mandal}</span><span className="flex items-center gap-1"><CalendarDays size={13} />{job.work_date}</span><span>₹{job.daily_wage}/రోజు</span><span><Users size={13} className="inline" /> {job.required_workers}</span>{job.distance_km !== null && <span>{job.distance_km} కి.మీ</span>}</p>
            {!isFarmer && job.status === 'OPEN' && <div className="mt-3 flex flex-wrap gap-2"><input aria-label="మీరు ఆశించే రోజు వేతనం" type="number" min="1" max="100000" value={jobWages[job.id] ?? job.daily_wage} onChange={(event) => setJobWages({ ...jobWages, [job.id]: event.target.value })} className="w-36 rounded-lg border border-slate-200 px-3 py-2" /><select aria-label="బృందాన్ని ఎంచుకోండి" value={jobWages[`team-${job.id}`] || ''} onChange={(event) => setJobWages({ ...jobWages, [`team-${job.id}`]: event.target.value })} className="rounded-lg border border-slate-200 px-2 py-2"><option value="">నేను మాత్రమే</option>{teams.map((team) => team.leader_id === account.id && <option key={team.id} value={team.id}>{team.name} ({team.members.length})</option>)}</select><button disabled={busy} onClick={() => void run(() => marketApi.apply(job.id, { proposed_wage: Number(jobWages[job.id] ?? job.daily_wage), team_id: jobWages[`team-${job.id}`] ? Number(jobWages[`team-${job.id}`]) : null }), 'దరఖాస్తు పంపబడింది.')} className="rounded-lg bg-leaf-600 px-3 py-2 text-sm font-bold text-white">దరఖాస్తు చేయండి</button></div>}
            {isFarmer && <div className="mt-3"><button onClick={() => void loadApplications(job.id)} className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-bold text-leaf-700">దరఖాస్తులు చూడండి</button>{appsByJob[job.id]?.map((application) => <div key={application.id} className="mt-2 rounded-xl bg-slate-50 p-3 text-sm"><div className="flex flex-wrap justify-between gap-2"><span className="font-bold">{application.worker_name}{application.team_name ? ` · ${application.team_name} (${application.team_size})` : ''}</span><span>{statusLabel(application.status)}</span></div><p className="mt-1 text-slate-600">ప్రతిపాదిత వేతనం: ₹{application.proposed_wage}/రోజు</p>{application.status === 'NEGOTIATING' && <div className="mt-2 flex flex-wrap gap-2"><input aria-label="ప్రతిపాదిత వేతనం సవరించండి" type="number" min="1" max="100000" value={applicationWages[application.id] ?? application.proposed_wage} onChange={(event) => setApplicationWages({ ...applicationWages, [application.id]: event.target.value })} className="w-36 rounded-lg border border-slate-200 px-3 py-2" /><button onClick={() => void run(() => marketApi.farmerOffer(application.id, { proposed_wage: Number(applicationWages[application.id] ?? application.proposed_wage) }), 'వేతన ప్రతిపాదన పంపబడింది.')} className="rounded-lg border border-leaf-300 px-3 py-2 text-sm font-bold text-leaf-700">కౌంటర్ ఆఫర్</button><button onClick={() => void run(() => marketApi.acceptApplication(application.id), 'బుకింగ్ కోసం నిర్ధారణ అభ్యర్థన పంపబడింది.')} className="rounded-lg bg-leaf-600 px-3 py-2 text-sm font-bold text-white">వేతనం అంగీకరించండి</button></div>}</div>)}</div>}
          </article>)}
        </section>}

        {tab === 'applications' && !isFarmer && <section className="space-y-3"><h2 className="text-lg font-bold text-slate-800">మీ దరఖాస్తులు</h2>{!applications.length && <p className="rounded-2xl bg-white p-5 text-sm text-slate-600">మీరు ఇంకా ఏ పనికీ దరఖాస్తు చేయలేదు.</p>}{applications.map((application) => <article key={application.id} className="rounded-2xl bg-white p-4 shadow-sm"><p className="font-bold text-slate-800">పని #{application.job_id}{application.team_name ? ` · ${application.team_name}` : ''}</p><p className="mt-1 text-sm">ప్రతిపాదిత వేతనం ₹{application.proposed_wage}/రోజు · {statusLabel(application.status)}</p>{application.status === 'NEGOTIATING' && <div className="mt-2 flex gap-2"><input aria-label="మీ ప్రతిపాదిత వేతనం" type="number" min="1" max="100000" value={applicationWages[application.id] ?? application.proposed_wage} onChange={(event) => setApplicationWages({ ...applicationWages, [application.id]: event.target.value })} className="w-36 rounded-lg border border-slate-200 px-3 py-2" /><button onClick={() => void run(() => marketApi.workerOffer(application.id, { proposed_wage: Number(applicationWages[application.id] ?? application.proposed_wage) }), 'వేతన ప్రతిపాదన పంపబడింది.')} className="rounded-lg bg-leaf-600 px-3 py-2 text-sm font-bold text-white">వేతనం ప్రతిపాదించండి</button></div>}</article>)}</section>}

        {tab === 'teams' && !isFarmer && <section className="space-y-4"><h2 className="text-lg font-bold text-slate-800">మీ కూలీ బృందాలు</h2><form onSubmit={(event) => { event.preventDefault(); void run(async () => { await marketApi.createTeam({ name: teamName }); setTeamName('') }, 'బృందం సృష్టించబడింది.') }} className="flex flex-wrap gap-2 rounded-2xl bg-white p-4"><input required minLength="2" maxLength="120" value={teamName} onChange={(event) => setTeamName(event.target.value)} placeholder="బృందం పేరు" className="min-w-0 flex-1 rounded-lg border border-slate-200 px-3 py-2" /><button className="rounded-lg bg-leaf-600 px-4 py-2 font-bold text-white">బృందం సృష్టించండి</button></form>{teams.map((team) => <article key={team.id} className="rounded-2xl bg-white p-4 shadow-sm"><h3 className="font-bold">{team.name} · {team.members.length} మంది</h3><ul className="mt-2 space-y-1 text-sm text-slate-600">{team.members.map((member) => <li key={member.id}>{member.name}{member.id === team.leader_id ? ' (నాయకుడు)' : ''}{team.leader_id === account.id && member.id !== team.leader_id && <button onClick={() => void run(() => marketApi.removeTeamMember(team.id, member.id), 'బృంద సభ్యుడిని తొలగించారు.')} className="ml-3 text-xs font-bold text-rose-700">తొలగించు</button>}</li>)}</ul>{team.leader_id === account.id && <form onSubmit={(event) => { event.preventDefault(); void run(async () => { await marketApi.addTeamMember(team.id, { phone: teamPhones[team.id] }); setTeamPhones({ ...teamPhones, [team.id]: '' }) }, 'సభ్యుడిని జోడించారు.') }} className="mt-3 flex flex-wrap gap-2"><input required type="tel" value={teamPhones[team.id] || ''} onChange={(event) => setTeamPhones({ ...teamPhones, [team.id]: event.target.value })} placeholder="సభ్యుని ఫోన్ నంబర్" className="min-w-0 flex-1 rounded-lg border border-slate-200 px-3 py-2" /><button className="rounded-lg border border-leaf-300 px-3 py-2 text-sm font-bold text-leaf-700">సభ్యుడిని జోడించండి</button></form>}</article>)}</section>}

        {tab === 'bookings' && <section className="space-y-3"><h2 className="text-lg font-bold text-slate-800">బుకింగ్‌లు</h2>{!bookings.length && <p className="rounded-2xl bg-white p-5 text-sm text-slate-600">బుకింగ్‌లు ఇంకా లేవు.</p>}{bookings.map((booking) => <article key={booking.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-white p-4 shadow-sm"><div><h3 className="font-bold">{booking.job_title} · {statusLabel(booking.status)}</h3><p className="mt-1 text-sm text-slate-600">{booking.village} · {booking.work_date} · ₹{booking.agreed_wage}/రోజు</p><p className="mt-1 text-sm text-slate-700">{isFarmer ? booking.worker_name : booking.farmer_name || 'రైతు సంప్రదింపు బుకింగ్ నిర్ధారణ తర్వాత కనిపిస్తుంది'}</p></div><div className="flex gap-2">{!isFarmer && booking.status === 'PENDING' && <button onClick={() => void run(() => marketApi.confirmBooking(booking.id), 'బుకింగ్ నిర్ధారించబడింది.')} className="flex items-center gap-1 rounded-lg bg-leaf-600 px-3 py-2 text-sm font-bold text-white"><Check size={15} /> నిర్ధారించండి</button>}{booking.status !== 'CANCELLED' && <button onClick={() => void run(() => isFarmer ? marketApi.cancelFarmerBooking(booking.id) : marketApi.cancelWorkerBooking(booking.id), 'బుకింగ్ రద్దు చేయబడింది.')} className="rounded-lg border border-rose-200 px-3 py-2 text-sm font-bold text-rose-700">రద్దు</button>}{booking.status === 'CONFIRMED' && (isFarmer ? booking.worker_phone : booking.farmer_phone) && <a href={`tel:${isFarmer ? booking.worker_phone : booking.farmer_phone}`} className="flex items-center gap-1 rounded-lg border border-leaf-300 px-3 py-2 text-sm font-bold text-leaf-700"><Phone size={15} /> కాల్</a>}</div></article>)}</section>}

        {tab === 'profile' && <form onSubmit={saveProfile} className="grid gap-4 rounded-2xl bg-white p-4 shadow-sm sm:grid-cols-2 sm:p-6"><h2 className="text-lg font-bold sm:col-span-2">మీ ప్రొఫైల్</h2>{field('పేరు', 'name', { required: true, minLength: 2, maxLength: 120, autoComplete: 'name' })}{field('గ్రామం', 'village', { maxLength: 120 })}{field('మండలం', 'mandal', { maxLength: 120 })}<label className="block text-sm font-bold text-slate-700">అక్షాంశం<input type="number" step="any" min="-90" max="90" value={profileForm.latitude ?? ''} onChange={(event) => setProfileForm({ ...profileForm, latitude: event.target.value })} className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" /></label><label className="block text-sm font-bold text-slate-700">రేఖాంశం<input type="number" step="any" min="-180" max="180" value={profileForm.longitude ?? ''} onChange={(event) => setProfileForm({ ...profileForm, longitude: event.target.value })} className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" /></label><button type="button" onClick={locate} className="flex items-center gap-2 justify-center rounded-xl border border-slate-200 px-3 py-2 text-sm font-bold"><LocateFixed size={16} /> నా స్థానం పొందండి</button>{!isFarmer && <>{field('పని నైపుణ్యాలు', 'skills', { maxLength: 1000, placeholder: 'ఉదా. పత్తి ఏరడం, విత్తడం' })}{field('అంచనా రోజు వేతనం (రూ.)', 'daily_wage', { type: 'number', min: 1, max: 100000 })}<label className="flex items-center gap-2 text-sm font-bold"><input type="checkbox" checked={Boolean(profileForm.is_available)} onChange={(event) => setProfileForm({ ...profileForm, is_available: event.target.checked })} className="h-4 w-4 accent-green-700" /> పనికి అందుబాటులో ఉన్నాను</label></>}<p className="text-xs text-slate-500 sm:col-span-2">{isFarmer ? `నమోదైన ఫోన్: ${profile?.phone || ''}` : `నమోదైన ఫోన్: ${profile?.phone || ''}`} · స్థాన సమాచారం దగ్గరి మ్యాచ్‌ల కోసం మాత్రమే ఉపయోగించబడుతుంది.</p><button disabled={busy} className="rounded-xl bg-leaf-600 py-3 font-bold text-white disabled:bg-slate-300 sm:col-span-2">ప్రొఫైల్ సేవ్ చేయండి</button></form>}
      </div>
    </main>
  ))
}

export default function Marketplace({ accountType, onBack, language }) {
  const [account, setAccount] = useState(() => {
    try {
      const saved = JSON.parse(window.sessionStorage.getItem('rythu-market-account') || 'null')
      return window.sessionStorage.getItem('rythu-market-token') && saved?.account_type === accountType ? saved : null
    } catch {
      return null
    }
  })
  const logout = () => {
    setMarketToken(null)
    setAccount(null)
    onBack()
  }
  const expire = () => {
    setMarketToken(null)
    setAccount(null)
  }

  return account
    ? <MarketplaceDashboard account={account} accountType={accountType} onLogout={logout} onSessionExpired={expire} language={language} />
    : <UsernameLogin accountType={accountType} onBack={onBack} onLogin={setAccount} language={language} />
}
