import { Sprout } from 'lucide-react'
import { translateTree } from '../i18n'

export default function Brand({ compact = false, language = 'te' }) {
  return translateTree(language, (
    <div className="flex items-center gap-3">
      <div className="grid h-11 w-11 place-items-center rounded-2xl bg-leaf-600 text-white shadow-lg shadow-green-900/15"><Sprout size={25} /></div>
      <div>
        <p className="text-lg font-extrabold leading-none text-leaf-700">రీతు సహాయ</p>
        {!compact && <p className="mt-1 text-[10px] font-bold tracking-[0.16em] text-slate-500">RYTHU SAHAYA</p>}
      </div>
    </div>
  ))
}
