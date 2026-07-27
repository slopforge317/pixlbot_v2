interface ParamSwitchProps {
  label: string
  checked: boolean
  onChange: (checked: boolean) => void
  isVariant?: boolean
}

export default function ParamSwitch({
  label,
  checked,
  onChange,
  isVariant,
}: ParamSwitchProps) {
  return (
    <div className="flex items-center justify-between px-1 py-2">
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-text-secondary">{label}</span>
        {isVariant && (
          <span className="text-[10px] text-accent-purple font-medium">Влияет на цену</span>
        )}
      </div>

      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-7 w-12 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
          checked ? 'bg-accent-purple' : 'bg-dark-border'
        }`}
      >
        <span
          className={`pointer-events-none inline-block h-6 w-6 rounded-full bg-white shadow-lg transform transition-transform duration-200 ease-in-out ${
            checked ? 'translate-x-5' : 'translate-x-0'
          }`}
        />
      </button>
    </div>
  )
}
