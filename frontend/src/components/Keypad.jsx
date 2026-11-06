import { Delete, Send } from 'lucide-react'
import { translateTree } from '../i18n'

const items = [
  'ఆకులు పసుపు రంగులో ఉన్నాయి', 'మూడు రోజుల నుంచి', 'పురుగులు కనిపిస్తున్నాయి',
  'సమస్య పెరుగుతోంది', 'ఫోటో పంపించాలి', 'నిపుణుడితో మాట్లాడాలి',
]

export default function Keypad({ onPick, onSend, onDelete, disabled, language = 'te' }) {
  return translateTree(language, (
    <div className="rounded-2xl border border-leaf-100 bg-leaf-50 p-3">
      <p className="mb-2 text-xs font-bold text-leaf-700">సులభ కీప్యాడ్</p>
      <div className="grid grid-cols-2 gap-2">
        {items.map((item) => <button key={item} type="button" disabled={disabled} onClick={() => onPick(item)} className="min-h-12 rounded-xl bg-white px-2 text-left text-xs font-semibold text-slate-700 shadow-sm hover:bg-leaf-100 disabled:opacity-50">{item}</button>)}
      </div>
      <div className="mt-2 grid grid-cols-2 gap-2">
        <button type="button" onClick={onDelete} disabled={disabled} className="flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white py-3 text-sm font-bold text-slate-700 disabled:opacity-50"><Delete size={17} /> తొలగించు</button>
        <button type="button" onClick={onSend} disabled={disabled} className="flex items-center justify-center gap-2 rounded-xl bg-leaf-600 py-3 text-sm font-bold text-white hover:bg-leaf-700 disabled:opacity-50"><Send size={17} /> పంపు</button>
      </div>
    </div>
  ))
}
