import { translateTree } from '../i18n'

const tones = {
  NEW: 'bg-sky-100 text-sky-700',
  INFORMATION_REQUIRED: 'bg-amber-100 text-amber-800',
  UNDER_REVIEW: 'bg-violet-100 text-violet-700',
  ASSIGNED: 'bg-indigo-100 text-indigo-700',
  GUIDANCE_PROVIDED: 'bg-teal-100 text-teal-700',
  FOLLOW_UP_PENDING: 'bg-orange-100 text-orange-700',
  RESOLVED: 'bg-emerald-100 text-emerald-700',
  ESCALATED: 'bg-rose-100 text-rose-700',
}

export default function StatusPill({ status, language = 'te' }) {
  const label = status?.replaceAll('_', ' ')
  return translateTree(language, (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ${tones[status] || 'bg-slate-100 text-slate-700'}`}>
      {label}
    </span>
  ))
}
