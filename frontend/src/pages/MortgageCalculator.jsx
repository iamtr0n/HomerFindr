import { useState, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Calculator, TrendingDown, DollarSign, PieChart, Table2, Home, Percent, ChevronDown, ChevronUp } from 'lucide-react'
import { useMortgage } from '../components/MortgageBar'

// --- Math helpers ---

function calcMonthlyPI(principal, annualRate, termYears) {
  if (!principal || !annualRate || !termYears) return 0
  const r = annualRate / 100 / 12
  const n = termYears * 12
  if (r === 0) return principal / n
  return principal * (r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1)
}

function calcAmortization(principal, annualRate, termYears) {
  const r = annualRate / 100 / 12
  const n = termYears * 12
  const payment = calcMonthlyPI(principal, annualRate, termYears)
  let balance = principal
  const rows = []
  for (let month = 1; month <= n; month++) {
    const interest = balance * r
    const principalPaid = payment - interest
    balance = Math.max(0, balance - principalPaid)
    const year = Math.ceil(month / 12)
    if (!rows[year - 1]) rows[year - 1] = { year, totalInterest: 0, totalPrincipal: 0, endBalance: 0 }
    rows[year - 1].totalInterest += interest
    rows[year - 1].totalPrincipal += principalPaid
    rows[year - 1].endBalance = balance
  }
  return rows
}

function fmt(n, compact = false) {
  if (!n && n !== 0) return '—'
  if (compact && n >= 1000000) return '$' + (n / 1000000).toFixed(2) + 'M'
  if (compact && n >= 1000) return '$' + Math.round(n / 1000) + 'K'
  return '$' + Math.round(n).toLocaleString()
}

// --- Input components ---

function NumberInput({ label, value, onChange, min, max, step = 1, prefix, suffix, placeholder, hint }) {
  return (
    <div className="space-y-1">
      <label className="block text-xs font-medium text-ink-muted">{label}</label>
      <div className="relative flex items-center">
        {prefix && <span className="absolute left-3 text-sm text-ink-muted pointer-events-none">{prefix}</span>}
        <input
          type="number"
          value={value ?? ''}
          onChange={e => onChange(e.target.value === '' ? '' : parseFloat(e.target.value))}
          min={min} max={max} step={step}
          placeholder={placeholder}
          className={`w-full bg-canvas-800 border border-canvas-600 rounded-lg py-2.5 text-sm text-ink-base focus:border-amber-500 focus:outline-none ${prefix ? 'pl-7' : 'pl-3'} ${suffix ? 'pr-10' : 'pr-3'}`}
        />
        {suffix && <span className="absolute right-3 text-sm text-ink-muted pointer-events-none">{suffix}</span>}
      </div>
      {hint && <p className="text-xs text-ink-muted">{hint}</p>}
    </div>
  )
}

function Select({ label, value, onChange, options }) {
  return (
    <div className="space-y-1">
      <label className="block text-xs font-medium text-ink-muted">{label}</label>
      <select
        value={value}
        onChange={e => onChange(+e.target.value)}
        className="w-full bg-canvas-800 border border-canvas-600 rounded-lg py-2.5 px-3 text-sm text-ink-base focus:border-amber-500 focus:outline-none"
      >
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  )
}

// --- Breakdown donut (simple CSS) ---

function PaymentBreakdown({ items }) {
  const total = items.reduce((s, i) => s + i.amount, 0)
  if (!total) return null
  let offset = 0
  const r = 40
  const circ = 2 * Math.PI * r

  return (
    <div className="flex items-center gap-6 flex-wrap">
      <svg width="100" height="100" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r={r} fill="none" stroke="#1e1e2e" strokeWidth="18" />
        {items.map((item, i) => {
          const pct = item.amount / total
          const dash = pct * circ
          const gap = circ - dash
          const el = (
            <circle
              key={i}
              cx="50" cy="50" r={r}
              fill="none"
              stroke={item.color}
              strokeWidth="18"
              strokeDasharray={`${dash} ${gap}`}
              strokeDashoffset={-offset * circ}
              transform="rotate(-90 50 50)"
              style={{ transition: 'stroke-dasharray 0.4s' }}
            />
          )
          offset += pct
          return el
        })}
        <text x="50" y="46" textAnchor="middle" style={{ fill: 'var(--ink-primary)' }} fontSize="9" fontWeight="600">{fmt(total)}</text>
        <text x="50" y="57" textAnchor="middle" style={{ fill: 'var(--ink-muted)' }} fontSize="7">/month</text>
      </svg>
      <div className="space-y-1.5">
        {items.map(item => (
          <div key={item.label} className="flex items-center gap-2 text-xs">
            <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: item.color }} />
            <span className="text-ink-muted w-28">{item.label}</span>
            <span className="font-mono font-semibold text-ink-base">{fmt(item.amount)}</span>
            <span className="text-ink-muted">({(item.amount / total * 100).toFixed(0)}%)</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// --- Affordability section ---

function AffordabilityCalc({ rate, termYears, downPct }) {
  const [income, setIncome] = useState('')
  const [monthlyDebt, setMonthlyDebt] = useState('')
  const [frontRatio, setFrontRatio] = useState(28)
  const [backRatio, setBackRatio] = useState(36)

  const result = useMemo(() => {
    const mo = (income || 0) / 12
    if (!mo) return null
    const maxPITI_front = mo * (frontRatio / 100)
    const maxPITI_back = mo * (backRatio / 100) - (monthlyDebt || 0)
    const maxPayment = Math.min(maxPITI_front, maxPITI_back)

    // Estimate taxes+insurance+pmi as ~1.5% of loan/yr → ~0.125%/mo of home price
    // Rough: monthly payment ≈ 85% P&I, 15% PITI overhead
    const piPayment = maxPayment * 0.85
    const r = (rate || 7) / 100 / 12
    const n = (termYears || 30) * 12
    let maxLoan = 0
    if (r > 0) {
      maxLoan = piPayment * (Math.pow(1 + r, n) - 1) / (r * Math.pow(1 + r, n))
    } else {
      maxLoan = piPayment * n
    }
    const maxPrice = maxLoan / (1 - (downPct || 20) / 100)
    return { maxPayment, maxLoan, maxPrice }
  }, [income, monthlyDebt, frontRatio, backRatio, rate, termYears, downPct])

  return (
    <div className="space-y-4">
      <p className="text-sm text-ink-muted">Enter your gross annual income to estimate how much home you can afford.</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <NumberInput label="Gross annual income" value={income} onChange={setIncome} prefix="$" step={1000} placeholder="120,000" />
        <NumberInput label="Monthly debts (car, student loans…)" value={monthlyDebt} onChange={setMonthlyDebt} prefix="$" step={50} placeholder="0" />
        <NumberInput label="Front-end ratio (housing)" value={frontRatio} onChange={setFrontRatio} suffix="%" min={20} max={40} step={1} hint="Lenders typically limit to 28%" />
        <NumberInput label="Back-end ratio (total debt)" value={backRatio} onChange={setBackRatio} suffix="%" min={28} max={50} step={1} hint="Lenders typically limit to 36–43%" />
      </div>
      {result && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-2">
          <div className="bg-canvas-800 border border-canvas-600 rounded-xl p-4 text-center">
            <p className="text-xs text-ink-muted mb-1">Max home price</p>
            <p className="text-2xl font-bold text-amber-400">{fmt(result.maxPrice)}</p>
          </div>
          <div className="bg-canvas-800 border border-canvas-600 rounded-xl p-4 text-center">
            <p className="text-xs text-ink-muted mb-1">Max loan amount</p>
            <p className="text-xl font-bold text-ink-base">{fmt(result.maxLoan)}</p>
          </div>
          <div className="bg-canvas-800 border border-canvas-600 rounded-xl p-4 text-center">
            <p className="text-xs text-ink-muted mb-1">Max monthly payment</p>
            <p className="text-xl font-bold text-ink-base">{fmt(result.maxPayment)}</p>
          </div>
        </div>
      )}
    </div>
  )
}

// --- Amortization table ---

function AmortizationTable({ rows }) {
  const [expanded, setExpanded] = useState(false)
  const visible = expanded ? rows : rows.slice(0, 5)

  return (
    <div className="space-y-2">
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-canvas-700 text-ink-muted">
              <th className="py-2 pr-4 text-left font-medium">Year</th>
              <th className="py-2 pr-4 text-right font-medium">Principal paid</th>
              <th className="py-2 pr-4 text-right font-medium">Interest paid</th>
              <th className="py-2 text-right font-medium">Remaining balance</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((row, i) => (
              <tr key={row.year} className={`border-b border-canvas-800 ${i % 2 === 0 ? '' : 'bg-canvas-900/30'}`}>
                <td className="py-2 pr-4 text-ink-muted">{row.year}</td>
                <td className="py-2 pr-4 text-right text-green-400 font-mono">{fmt(row.totalPrincipal)}</td>
                <td className="py-2 pr-4 text-right text-red-400/80 font-mono">{fmt(row.totalInterest)}</td>
                <td className="py-2 text-right text-ink-base font-mono">{fmt(row.endBalance)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length > 5 && (
        <button
          onClick={() => setExpanded(v => !v)}
          className="flex items-center gap-1 text-xs text-ink-muted hover:text-ink-base transition-colors"
        >
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          {expanded ? 'Show less' : `Show all ${rows.length} years`}
        </button>
      )}
    </div>
  )
}

// --- State average effective property tax rates (%) ---
// Source: Tax Foundation / Census data averages; user can always override.
const STATE_TAX_RATES = {
  AL: 0.40, AK: 0.58, AZ: 0.62, AR: 0.63, CA: 0.73, CO: 0.51, CT: 1.79,
  DE: 0.57, FL: 0.89, GA: 0.92, HI: 0.32, ID: 0.69, IL: 2.23, IN: 0.87,
  IA: 1.53, KS: 1.41, KY: 0.86, LA: 0.55, ME: 1.36, MD: 1.07, MA: 1.20,
  MI: 1.54, MN: 1.12, MS: 0.65, MO: 0.97, MT: 0.84, NE: 1.73, NV: 0.48,
  NH: 2.09, NJ: 2.47, NM: 0.67, NY: 1.73, NC: 0.80, ND: 0.98, OH: 1.59,
  OK: 0.90, OR: 0.91, PA: 1.58, RI: 1.53, SC: 0.57, SD: 1.17, TN: 0.66,
  TX: 1.60, UT: 0.56, VT: 1.78, VA: 0.87, WA: 0.93, WV: 0.57, WI: 1.73,
  WY: 0.61, DC: 0.55,
}

// --- Main page ---

const TABS = [
  { id: 'calculator', label: 'Calculator', Icon: Calculator },
  { id: 'affordability', label: 'Affordability', Icon: Home },
  { id: 'amortization', label: 'Amortization', Icon: Table2 },
]

export default function MortgageCalculator() {
  const { settings: globalSettings } = useMortgage()
  const [searchParams] = useSearchParams()

  // Seed from URL params (set by "Mortgage Calc →" on listing cards)
  const seedPrice = parseInt(searchParams.get('price') || '0', 10) || 400000
  const seedHoa   = parseFloat(searchParams.get('hoa') || '0') || 0
  const seedState = (searchParams.get('state') || '').toUpperCase().trim()
  const stateTaxRate = seedState ? (STATE_TAX_RATES[seedState] ?? null) : null

  // Loan inputs — seed from URL param or global mortgage bar settings
  const [homePrice, setHomePrice] = useState(seedPrice)
  const [downAmt, setDownAmt] = useState(() => Math.round(seedPrice * ((globalSettings.downPct || 20) / 100)))
  const [rate, setRate] = useState(globalSettings.rate || 7.0)
  const [termYears, setTermYears] = useState(globalSettings.termYears || 30)
  const [propTaxRate, setPropTaxRate] = useState(stateTaxRate ?? 1.2)
  const [insuranceAnnual, setInsuranceAnnual] = useState(1500)
  const [hoaMonthly, setHoaMonthly] = useState(seedHoa)
  const [pmiRate, setPmiRate] = useState(0.5)           // % of loan annually

  const [tab, setTab] = useState('calculator')

  // Derived values
  const downPct = homePrice > 0 ? (downAmt / homePrice) * 100 : 0
  const loanAmount = Math.max(0, homePrice - downAmt)
  const hasPMI = downPct < 20 && loanAmount > 0

  const monthlyPI = calcMonthlyPI(loanAmount, rate, termYears)
  const monthlyTax = (homePrice * (propTaxRate / 100)) / 12
  const monthlyInsurance = insuranceAnnual / 12
  const monthlyPMI = hasPMI ? (loanAmount * (pmiRate / 100)) / 12 : 0
  const totalMonthly = monthlyPI + monthlyTax + monthlyInsurance + monthlyPMI + (hoaMonthly || 0)

  const amortRows = useMemo(() => (
    loanAmount > 0 && rate > 0 ? calcAmortization(loanAmount, rate, termYears) : []
  ), [loanAmount, rate, termYears])

  const totalInterest = amortRows.reduce((s, r) => s + r.totalInterest, 0)
  const totalCost = loanAmount + totalInterest + (monthlyTax + monthlyInsurance + (hoaMonthly || 0)) * termYears * 12

  // Dynamic hint for the property tax field
  const taxHint = homePrice > 0
    ? `~${fmt(monthlyTax)}/mo · ${fmt(monthlyTax * 12)}/yr${stateTaxRate != null ? ` · ${seedState} avg` : ''}`
    : stateTaxRate != null ? `${seedState} state avg · check county assessor for exact rate` : 'US avg ~1.1%; check county records'

  const breakdownItems = [
    { label: 'Principal & Interest', amount: monthlyPI, color: '#f59e0b' },
    { label: 'Property Tax', amount: monthlyTax, color: '#60a5fa' },
    { label: 'Insurance', amount: monthlyInsurance, color: '#34d399' },
    ...(hasPMI ? [{ label: 'PMI', amount: monthlyPMI, color: '#f87171' }] : []),
    ...(hoaMonthly > 0 ? [{ label: 'HOA', amount: hoaMonthly, color: '#a78bfa' }] : []),
  ]

  // Sync downAmt when homePrice changes (keep percentage)
  function handleHomePriceChange(val) {
    const p = val || 0
    setHomePrice(p)
    setDownAmt(Math.round(p * (downPct / 100)))
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink-primary flex items-center gap-2">
          <Calculator size={22} className="text-amber-400" />
          Mortgage Calculator
        </h1>
        <p className="text-sm text-ink-muted mt-1">Full PITI breakdown, affordability analysis, and amortization schedule.</p>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-1 bg-canvas-900 border border-canvas-700 rounded-xl p-1 w-fit max-w-full">
        {TABS.map(({ id, label, Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 text-xs sm:text-sm rounded-lg transition-colors ${
              tab === id ? 'bg-amber-500/20 text-amber-400 font-medium' : 'text-ink-muted hover:text-ink-base'
            }`}
          >
            <Icon size={13} />
            <span className="hidden xs:inline">{label}</span>
            <span className="xs:hidden">{label.split(' ')[0]}</span>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Inputs panel */}
        <div className="lg:col-span-2 bg-canvas-900 border border-canvas-700 rounded-2xl p-5 space-y-4 h-fit">
          <p className="text-sm font-semibold text-ink-base">Loan Details</p>

          <NumberInput
            label="Home price"
            value={homePrice}
            onChange={handleHomePriceChange}
            prefix="$" step={1000} min={0}
          />

          <div className="grid grid-cols-2 gap-3">
            <NumberInput
              label="Down payment ($)"
              value={downAmt}
              onChange={setDownAmt}
              prefix="$" step={1000} min={0}
            />
            <NumberInput
              label="Down payment (%)"
              value={parseFloat(downPct.toFixed(1))}
              onChange={pct => setDownAmt(Math.round(homePrice * (pct / 100)))}
              suffix="%" step={0.5} min={0} max={100}
            />
          </div>

          {hasPMI && (
            <div className="flex items-center gap-1.5 text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-1.5">
              <Percent size={11} />
              PMI applies — down payment is under 20%
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <NumberInput label="Interest rate" value={rate} onChange={setRate} suffix="%" step={0.05} min={0} />
            <Select
              label="Loan term"
              value={termYears}
              onChange={setTermYears}
              options={[
                { value: 10, label: '10 years' },
                { value: 15, label: '15 years' },
                { value: 20, label: '20 years' },
                { value: 30, label: '30 years' },
              ]}
            />
          </div>

          <div className="border-t border-canvas-700 pt-4 space-y-3">
            <p className="text-xs font-semibold text-ink-muted uppercase tracking-wide">Additional Costs</p>
            <NumberInput label="Property tax rate" value={propTaxRate} onChange={setPropTaxRate} suffix="% / yr" step={0.1} min={0} hint={taxHint} />
            <NumberInput label="Home insurance" value={insuranceAnnual} onChange={setInsuranceAnnual} prefix="$" suffix="/ yr" step={100} min={0} />
            <NumberInput label="HOA" value={hoaMonthly || ''} onChange={setHoaMonthly} prefix="$" suffix="/ mo" step={25} min={0} />
            {hasPMI && (
              <NumberInput label="PMI rate" value={pmiRate} onChange={setPmiRate} suffix="% / yr" step={0.05} min={0} hint="Typically 0.3–1.5% of loan" />
            )}
          </div>
        </div>

        {/* Results panel */}
        <div className="lg:col-span-3 space-y-4">

          {tab === 'calculator' && (
            <>
              {/* Monthly total hero */}
              <div className="bg-gradient-to-br from-amber-500/10 to-canvas-900 border border-amber-500/20 rounded-2xl p-5">
                <p className="text-xs text-ink-muted mb-1">Estimated monthly payment</p>
                <p className="text-4xl font-bold text-amber-400 font-mono">{fmt(totalMonthly)}<span className="text-lg text-ink-muted font-normal"> /mo</span></p>
                <p className="text-xs text-ink-muted mt-1">{fmt(loanAmount)} loan · {termYears} yr · {rate}%</p>
              </div>

              {/* Breakdown donut */}
              <div className="bg-canvas-900 border border-canvas-700 rounded-2xl p-5">
                <p className="text-sm font-semibold text-ink-base mb-4 flex items-center gap-2"><PieChart size={14} className="text-amber-400" /> Payment Breakdown</p>
                <PaymentBreakdown items={breakdownItems} />
              </div>

              {/* Cost summary */}
              <div className="bg-canvas-900 border border-canvas-700 rounded-2xl p-5 space-y-3">
                <p className="text-sm font-semibold text-ink-base flex items-center gap-2"><TrendingDown size={14} className="text-amber-400" /> Cost Summary</p>
                <div className="space-y-2">
                  {[
                    { label: 'Loan amount', value: loanAmount },
                    { label: 'Down payment', value: downAmt, sub: `(${downPct.toFixed(1)}%)` },
                    { label: 'Total interest paid', value: totalInterest, cls: 'text-red-400/80' },
                    { label: `Total P&I over ${termYears} yrs`, value: loanAmount + totalInterest },
                    { label: `Est. total cost (incl. taxes, insurance${hoaMonthly > 0 ? ' + HOA' : ''})`, value: totalCost, cls: 'text-amber-400 font-semibold' },
                  ].map(row => (
                    <div key={row.label} className="flex justify-between items-baseline text-sm">
                      <span className="text-ink-muted">{row.label} {row.sub && <span className="text-xs">{row.sub}</span>}</span>
                      <span className={`font-mono ${row.cls || 'text-ink-base'}`}>{fmt(row.value)}</span>
                    </div>
                  ))}
                </div>
                <div className="border-t border-canvas-700 pt-3">
                  <p className="text-xs text-ink-muted flex items-center gap-1">
                    <DollarSign size={11} />
                    For every $100K borrowed at {rate}% for {termYears} yr, you pay {fmt(calcMonthlyPI(100000, rate, termYears))}/mo
                  </p>
                </div>
              </div>

              {/* Rate comparison */}
              <div className="bg-canvas-900 border border-canvas-700 rounded-2xl p-5">
                <p className="text-sm font-semibold text-ink-base mb-3">Rate Comparison</p>
                <div className="space-y-2">
                  {[-1, -0.5, 0, 0.5, 1].map(delta => {
                    const r2 = Math.max(0.1, rate + delta)
                    const mo = calcMonthlyPI(loanAmount, r2, termYears) + monthlyTax + monthlyInsurance + monthlyPMI + (hoaMonthly || 0)
                    const diff = mo - totalMonthly
                    return (
                      <div key={delta} className={`flex justify-between items-center text-sm py-1 px-2 rounded-lg ${delta === 0 ? 'bg-amber-500/10 border border-amber-500/20' : ''}`}>
                        <span className={`${delta === 0 ? 'text-amber-400 font-medium' : 'text-ink-muted'}`}>{r2.toFixed(2)}%{delta === 0 ? ' (current)' : ''}</span>
                        <div className="flex items-center gap-4">
                          <span className="font-mono text-ink-base">{fmt(mo)}/mo</span>
                          {delta !== 0 && (
                            <span className={`text-xs font-mono w-20 text-right ${diff > 0 ? 'text-red-400' : 'text-green-400'}`}>
                              {diff > 0 ? '+' : ''}{fmt(diff)}/mo
                            </span>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </>
          )}

          {tab === 'affordability' && (
            <div className="bg-canvas-900 border border-canvas-700 rounded-2xl p-5">
              <p className="text-sm font-semibold text-ink-base mb-4 flex items-center gap-2"><Home size={14} className="text-amber-400" /> How Much Can You Afford?</p>
              <AffordabilityCalc rate={rate} termYears={termYears} downPct={downPct} />
            </div>
          )}

          {tab === 'amortization' && (
            <div className="bg-canvas-900 border border-canvas-700 rounded-2xl p-5 space-y-4">
              <p className="text-sm font-semibold text-ink-base flex items-center gap-2"><Table2 size={14} className="text-amber-400" /> Amortization Schedule</p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-center">
                <div className="bg-canvas-800 rounded-xl p-3">
                  <p className="text-xs text-ink-muted">Total interest</p>
                  <p className="text-lg font-bold text-red-400 font-mono">{fmt(totalInterest, true)}</p>
                </div>
                <div className="bg-canvas-800 rounded-xl p-3">
                  <p className="text-xs text-ink-muted">Total principal</p>
                  <p className="text-lg font-bold text-green-400 font-mono">{fmt(loanAmount, true)}</p>
                </div>
                <div className="bg-canvas-800 rounded-xl p-3">
                  <p className="text-xs text-ink-muted">Interest ratio</p>
                  <p className="text-lg font-bold text-ink-base">{loanAmount > 0 ? ((totalInterest / (loanAmount + totalInterest)) * 100).toFixed(0) : 0}%</p>
                </div>
              </div>
              {amortRows.length > 0 ? (
                <AmortizationTable rows={amortRows} />
              ) : (
                <p className="text-sm text-ink-muted">Enter loan details to see the amortization schedule.</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
