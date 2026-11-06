import { useEffect, useRef, useState } from 'react'
import { ArrowRight, BriefcaseBusiness, MapPin, Mic, Phone, Search, UserRound, Users, X } from 'lucide-react'
import Brand from '../components/Brand'
import { marketApi, resolveProfilePhotoUrl } from '../services/api'
import { translateTree } from '../i18n'

function listingError(error) {
  const detail = error.response?.data?.detail
  return typeof detail === 'string' ? detail : 'మార్కెట్‌ప్లేస్ వివరాలను లోడ్ చేయలేకపోయాము. మళ్లీ ప్రయత్నించండి.'
}

export default function FarmerAssistant({ onFarmerLogin, onWorkerLogin, language }) {
  const [profileMenuOpen, setProfileMenuOpen] = useState(false)
  const [section, setSection] = useState('jobs')
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [jobs, setJobs] = useState([])
  const [workers, setWorkers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [profileView, setProfileView] = useState(null)
  const profileRequestId = useRef(0)

  const openProfile = async (accountType, accountId) => {
    const requestId = profileRequestId.current + 1
    profileRequestId.current = requestId
    setProfileView({ loading: true })
    try {
      const { data } = await marketApi.publicProfile(accountType, accountId)
      if (profileRequestId.current === requestId) setProfileView({ data })
    } catch (requestError) {
      if (profileRequestId.current === requestId) {
        setProfileView({ error: listingError(requestError) })
      }
    }
  }

  const closeProfile = () => {
    profileRequestId.current += 1
    setProfileView(null)
  }

  useEffect(() => {
    let active = true
    const timer = window.setTimeout(async () => {
      setLoading(true)
      setError('')
      try {
        const [jobsResponse, workersResponse] = await Promise.all([
          marketApi.publicJobs(search.trim()),
          marketApi.publicWorkers(search.trim()),
        ])
        if (active) {
          setJobs(jobsResponse.data)
          setWorkers(workersResponse.data)
        }
      } catch (requestError) {
        if (active) setError(listingError(requestError))
      } finally {
        if (active) setLoading(false)
      }
    }, search ? 250 : 0)

    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [search])

  useEffect(() => {
    if (!profileMenuOpen) return undefined

    const closeOnOutsideClick = (event) => {
      if (!event.target.closest('[data-profile-menu]')) setProfileMenuOpen(false)
    }
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') setProfileMenuOpen(false)
    }
    document.addEventListener('click', closeOnOutsideClick)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('click', closeOnOutsideClick)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [profileMenuOpen])

  useEffect(() => {
    if (!profileView) return undefined
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') closeProfile()
    }
    document.addEventListener('keydown', closeOnEscape)
    return () => document.removeEventListener('keydown', closeOnEscape)
  }, [profileView])

  const selectSignIn = (onSelect) => {
    setProfileMenuOpen(false)
    onSelect()
  }

  return translateTree(language, (
    <main className="min-h-[calc(100vh-3rem)] bg-slate-50">
      <header className="border-b border-slate-200 bg-white px-4 py-4 sm:px-8">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <Brand language={language} />
          <div className="relative" data-profile-menu>
            <button
              type="button"
              aria-label={language === 'en' ? 'Profile and sign-in options' : 'ప్రొఫైల్ మరియు సైన్ ఇన్ ఎంపికలు'}
              aria-haspopup="menu"
              aria-expanded={profileMenuOpen}
              aria-controls="profile-menu"
              onClick={() => setProfileMenuOpen((open) => !open)}
              className="grid h-11 w-11 place-items-center rounded-full border border-leaf-200 bg-white text-leaf-700 shadow-sm hover:bg-leaf-50"
            >
              <UserRound size={22} />
            </button>
            {profileMenuOpen && (
              <div id="profile-menu" role="menu" className="absolute right-0 z-10 mt-2 w-52 rounded-2xl border border-slate-100 bg-white p-2 shadow-xl">
                <button type="button" role="menuitem" onClick={() => selectSignIn(onFarmerLogin)} className="w-full rounded-xl bg-leaf-600 px-4 py-3 text-left font-bold text-white hover:bg-leaf-700">
                  రైతు లాగిన్
                </button>
                <button type="button" role="menuitem" onClick={() => selectSignIn(onWorkerLogin)} className="mt-1 w-full rounded-xl px-4 py-3 text-left font-bold text-leaf-700 hover:bg-leaf-50">
                  కూలీ లాగిన్
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <section className="bg-gradient-to-br from-leaf-700 to-leaf-900 px-4 py-12 text-white sm:py-16">
        <div className="mx-auto max-w-4xl text-center">
          <h1 className="text-3xl font-extrabold sm:text-5xl">పని కోసం వెతకండి. మంచి కూలీలను కనుగొనండి.</h1>
          <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-leaf-50 sm:text-base">
            మీ ప్రాంతంలోని పని అవకాశాలు మరియు అందుబాటులో ఉన్న కూలీలను ఒకేచోట చూడండి.
          </p>
          <form
            onSubmit={(event) => {
              event.preventDefault()
              setSearch(searchInput.trim())
            }}
            className="mx-auto mt-7 flex max-w-2xl items-center gap-3 rounded-2xl bg-white px-4 py-2 text-slate-500 shadow-xl"
          >
            <Search size={22} className="shrink-0" />
            <input
              type="search"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="పని, కూలీ లేదా రైతు పేరు వెతకండి"
              className="min-w-0 flex-1 border-0 py-2 text-sm text-slate-800 outline-none placeholder:text-slate-400 focus-visible:outline-none"
            />
            <button type="submit" className="rounded-lg bg-leaf-600 px-4 py-2 text-sm font-bold text-white hover:bg-leaf-700">వెతకండి</button>
          </form>
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-3 px-4 pt-6 sm:grid-cols-3 sm:px-8" aria-label="Choose your role">
        <button type="button" onClick={onFarmerLogin} className="flex min-h-28 items-center justify-between rounded-2xl border border-leaf-100 bg-white p-5 text-left shadow-sm hover:border-leaf-300">
          <span><strong className="block text-lg text-slate-800">నేను రైతును</strong><span className="mt-1 block text-sm text-slate-600">పని నమోదు చేసి కూలీలను కనుగొనండి</span></span><ArrowRight className="text-leaf-700" />
        </button>
        <button type="button" onClick={onWorkerLogin} className="flex min-h-28 items-center justify-between rounded-2xl border border-leaf-100 bg-white p-5 text-left shadow-sm hover:border-leaf-300">
          <span><strong className="block text-lg text-slate-800">నేను కూలీని</strong><span className="mt-1 block text-sm text-slate-600">దగ్గరి పనులు మరియు బృందాలను చూడండి</span></span><ArrowRight className="text-leaf-700" />
        </button>
        <button type="button" onClick={onFarmerLogin} className="flex min-h-28 items-center justify-between rounded-2xl bg-leaf-50 p-5 text-left shadow-sm hover:bg-leaf-100">
          <span><strong className="block text-lg text-leaf-900">వాయిస్‌తో పని నమోదు</strong><span className="mt-1 block text-sm text-slate-600">రైతు ఖాతాలో తెలుగు వాయిస్ టైపింగ్</span></span><Mic className="text-leaf-700" />
        </button>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-8 sm:px-8">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-2xl font-extrabold text-slate-800">మీకు కావలసినదాన్ని ఎంచుకోండి</h2>
            <p className="mt-1 text-sm text-slate-500">పని ప్రకటనలు లేదా అందుబాటులో ఉన్న కూలీలను చూడండి</p>
          </div>
          <div className="flex rounded-xl bg-slate-200 p-1" role="tablist" aria-label="Marketplace sections">
            <button
              type="button"
              role="tab"
              aria-selected={section === 'jobs'}
              onClick={() => setSection('jobs')}
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-bold ${section === 'jobs' ? 'bg-white text-leaf-700 shadow-sm' : 'text-slate-600'}`}
            >
              <BriefcaseBusiness size={17} /> రిక్రూటర్లు
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={section === 'workers'}
              onClick={() => setSection('workers')}
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-bold ${section === 'workers' ? 'bg-white text-leaf-700 shadow-sm' : 'text-slate-600'}`}
            >
              <Users size={17} /> కూలీలు
            </button>
          </div>
        </div>

        {error && <p role="alert" className="mb-5 rounded-xl bg-rose-50 p-4 text-sm text-rose-800">{error}</p>}
        {loading ? (
          <p role="status" className="py-16 text-center text-slate-500">వివరాలు లోడ్ అవుతున్నాయి…</p>
        ) : section === 'jobs' ? (
          jobs.length ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {jobs.map((job) => (
                <article key={job.id} className="flex flex-col rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
                  <div className="flex items-start justify-between gap-3">
                    <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-amber-50 text-amber-700"><BriefcaseBusiness size={22} /></div>
                    <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700">కూలీలు కావాలి</span>
                  </div>
                  <h3 className="mt-4 text-lg font-extrabold text-slate-800">{job.title}</h3>
                  <button type="button" onClick={() => void openProfile('farmer', job.recruiter_id)} className="mt-1 flex items-center gap-2 text-left text-sm text-slate-500 hover:text-leaf-700">
                    {job.recruiter_photo_url
                      ? <img src={resolveProfilePhotoUrl(job.recruiter_photo_url)} alt="" className="h-7 w-7 rounded-full object-cover" />
                      : <span className="grid h-7 w-7 place-items-center rounded-full bg-leaf-50 text-leaf-700"><UserRound size={15} /></span>}
                    <span>{job.recruiter_name} · రిక్రూటర్ · </span>
                    <span className="font-bold text-leaf-700">ప్రొఫైల్ చూడండి</span>
                  </button>
                  {job.description && <p className="mt-3 line-clamp-2 text-sm leading-5 text-slate-600">{job.description}</p>}
                  <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-sm text-slate-600">
                    <span className="flex items-center gap-1"><MapPin size={16} /> {job.village}, {job.mandal}</span>
                    <span>{new Date(`${job.work_date}T00:00:00`).toLocaleDateString(language === 'en' ? 'en-IN' : 'te-IN')}</span>
                  </div>
                  <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-4">
                    <div><span className="font-extrabold text-leaf-700">₹{job.daily_wage}</span><span className="text-xs text-slate-500"> / రోజు</span><p className="mt-1 text-xs text-slate-500">{job.required_workers} మంది అవసరం</p></div>
                    <button type="button" onClick={onWorkerLogin} className="flex items-center gap-1 rounded-xl bg-leaf-600 px-4 py-2.5 text-sm font-bold text-white hover:bg-leaf-700">
                      పని చేయండి <ArrowRight size={16} />
                    </button>
                  </div>
                </article>
              ))}
            </div>
          ) : <p className="rounded-2xl bg-white py-16 text-center text-slate-500 shadow-sm">ప్రస్తుతం పని ప్రకటనలు లేవు. తర్వాత మళ్లీ చూడండి.</p>
        ) : (
          workers.length ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {workers.map((worker) => (
                <article key={worker.id} className="flex flex-col rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
                  <div className="flex items-center gap-3">
                    <button type="button" onClick={() => void openProfile('worker', worker.id)} aria-label={`${worker.name} ప్రొఫైల్ చూడండి`} className="grid h-16 w-16 shrink-0 place-items-center overflow-hidden rounded-full border-2 border-white bg-leaf-50 text-leaf-700 shadow-sm">
                      {worker.profile_photo_url ? <img src={resolveProfilePhotoUrl(worker.profile_photo_url)} alt={`${worker.name} ప్రొఫైల్ ఫోటో`} className="h-full w-full object-cover" /> : <UserRound size={28} />}
                    </button>
                    <div className="min-w-0 flex-1">
                      <h3 className="truncate font-extrabold text-slate-800">{worker.name}</h3>
                      <p className="mt-1 flex items-center gap-1 text-sm text-slate-500"><MapPin size={15} />{worker.village || worker.mandal || 'స్థానం నమోదు కాలేదు'}</p>
                    </div>
                    <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700">అందుబాటులో</span>
                  </div>
                  <button type="button" onClick={() => void openProfile('worker', worker.id)} className="mt-2 self-start text-sm font-bold text-leaf-700 hover:underline">ప్రొఫైల్ చూడండి</button>
                  <p className="mt-4 min-h-10 text-sm leading-5 text-slate-600">{worker.skills || 'నైపుణ్యాలు నమోదు కాలేదు'}</p>
                  <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-4">
                    <div><span className="font-extrabold text-leaf-700">{worker.daily_wage ? `₹${worker.daily_wage}` : 'వేతనం చర్చించండి'}</span>{worker.daily_wage && <span className="text-xs text-slate-500"> / రోజు</span>}</div>
                    <button type="button" onClick={onFarmerLogin} className="flex items-center gap-1 rounded-xl bg-leaf-600 px-4 py-2.5 text-sm font-bold text-white hover:bg-leaf-700">
                      కూలీని రిక్రూట్ చేయండి <ArrowRight size={16} />
                    </button>
                  </div>
                </article>
              ))}
            </div>
          ) : <p className="rounded-2xl bg-white py-16 text-center text-slate-500 shadow-sm">ప్రస్తుతం అందుబాటులో ఉన్న కూలీలు లేరు.</p>
        )}
      </section>
      {profileView && (
        <div className="fixed inset-0 z-30 flex items-center justify-center bg-slate-950/50 p-4" onMouseDown={(event) => {
          if (event.target === event.currentTarget) closeProfile()
        }}>
          <section role="dialog" aria-modal="true" aria-labelledby="public-profile-title" className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mb-5 flex items-start justify-between gap-4">
              <h2 id="public-profile-title" className="text-xl font-extrabold text-slate-800">
                {profileView.data?.account_type === 'worker' ? 'కూలీ ప్రొఫైల్' : 'రిక్రూటర్ ప్రొఫైల్'}
              </h2>
              <button type="button" onClick={closeProfile} aria-label="మూసివేయండి" className="rounded-full p-2 text-slate-500 hover:bg-slate-100"><X size={20} /></button>
            </div>
            {profileView.loading && <p role="status" className="py-10 text-center text-slate-500">వివరాలు లోడ్ అవుతున్నాయి…</p>}
            {profileView.error && <p role="alert" className="rounded-xl bg-rose-50 p-4 text-sm text-rose-800">{profileView.error}</p>}
            {profileView.data && (() => {
              const profile = profileView.data
              const location = [profile.village, profile.mandal].filter(Boolean).join(', ')
              return (
                <>
                  <div className="flex items-center gap-4">
                    <div className="grid h-20 w-20 shrink-0 place-items-center overflow-hidden rounded-full bg-leaf-50 text-leaf-700">
                      {profile.profile_photo_url ? <img src={resolveProfilePhotoUrl(profile.profile_photo_url)} alt="" className="h-full w-full object-cover" /> : <UserRound size={34} />}
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-lg font-bold text-slate-800">{profile.name}</h3>
                      <p className="text-sm text-slate-500">{profile.account_type === 'worker' ? 'కూలీ' : 'రిక్రూటర్'}</p>
                    </div>
                  </div>
                  <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
                    <div><dt className="font-bold text-slate-500">ఫోన్ నంబర్</dt><dd className="mt-1">{profile.phone ? <a href={`tel:${profile.phone}`} className="flex items-center gap-1 text-leaf-700 underline"><Phone size={15} />{profile.phone}</a> : 'ఫోన్ సంప్రదింపుకు అనుమతి ఇవ్వలేదు'}</dd></div>
                    <div><dt className="font-bold text-slate-500">ప్రాంతం</dt><dd className="mt-1">{location || 'నమోదు కాలేదు'}</dd></div>
                    {profile.account_type === 'worker' ? (
                      <>
                        <div className="sm:col-span-2"><dt className="font-bold text-slate-500">నైపుణ్యాలు</dt><dd className="mt-1">{profile.skills || 'నమోదు కాలేదు'}</dd></div>
                        <div><dt className="font-bold text-slate-500">రోజు వేతనం</dt><dd className="mt-1">{profile.daily_wage ? `₹${profile.daily_wage} / రోజు` : 'వేతనం చర్చించండి'}</dd></div>
                        <div><dt className="font-bold text-slate-500">పని స్థితి</dt><dd className="mt-1">{profile.is_available ? 'అందుబాటులో' : 'ప్రస్తుతం అందుబాటులో లేరు'}</dd></div>
                      </>
                    ) : (
                      <div className="sm:col-span-2">
                        <dt className="font-bold text-slate-500">ప్రస్తుత పని ప్రకటనలు</dt>
                        <dd className="mt-2 space-y-2">
                          {profile.jobs.length
                            ? profile.jobs.map((job) => <div key={job.id} className="rounded-xl bg-slate-50 p-3"><p className="font-bold">{job.title}</p><p className="mt-1 text-xs text-slate-500">{job.work_date} · ₹{job.daily_wage} / రోజు · {job.required_workers} మంది అవసరం</p></div>)
                            : 'పని వివరాలు లేవు'}
                        </dd>
                      </div>
                    )}
                  </dl>
                </>
              )
            })()}
          </section>
        </div>
      )}
    </main>
  ))
}
