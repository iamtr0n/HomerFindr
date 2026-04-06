import { useState, useMemo, useEffect } from 'react'
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

// --- Affordability / Budget Planner ---

function AffordabilityCalc({ rate, termYears, downPct, totalMonthly, seedState }) {
  // ── Income ──────────────────────────────────────────────────────
  const [salary1, setSalary1] = useState('')
  const [extra1,  setExtra1]  = useState('')
  const [bonus1,  setBonus1]  = useState('')
  const [hasCo,   setHasCo]   = useState(false)
  const [salary2, setSalary2] = useState('')
  const [extra2,  setExtra2]  = useState('')
  const [bonus2,  setBonus2]  = useState('')

  // ── Tax ─────────────────────────────────────────────────────────
  const [taxState, setTaxState] = useState(seedState || '')
  const [filing,   setFiling]   = useState('single')
  useEffect(() => { setFiling(hasCo ? 'mfj' : 'single') }, [hasCo])

  // ── Expenses ─────────────────────────────────────────────────────
  const [foodWeekly,    setFoodWeekly]    = useState('')
  const [carPayments,   setCarPayments]   = useState('')
  const [healthIns,     setHealthIns]     = useState('')
  const [utilities,     setUtilities]     = useState('')
  const [subscriptions, setSubscriptions] = useState('')
  const [vacationAnnual,setVacationAnnual]= useState('')
  const [otherMonthly,  setOtherMonthly]  = useState('')

  // ── Lender ratios ────────────────────────────────────────────────
  const [frontRatio, setFrontRatio] = useState(28)
  const [backRatio,  setBackRatio]  = useState(36)

  const calcs = useMemo(() => {
    const gross1 = (salary1 || 0) + (extra1 || 0) + (bonus1 || 0)
    const gross2 = hasCo ? ((salary2 || 0) + (extra2 || 0) + (bonus2 || 0)) : 0
    const grossTotal = gross1 + gross2
    if (!grossTotal) return null

    const federalTax = calcFederalTax(grossTotal, filing)
    const fica1      = calcFICA((salary1 || 0) + (extra1 || 0))
    const fica2      = hasCo ? calcFICA((salary2 || 0) + (extra2 || 0)) : 0
    const ficaTotal  = fica1 + fica2
    const stateKey   = taxState.toUpperCase()
    const stateRate  = taxState ? (STATE_INCOME_TAX_RATES[stateKey] ?? null) : null
    const stateTax   = stateRate != null ? grossTotal * (stateRate / 100) : 0
    const totalTax   = federalTax + ficaTotal + stateTax
    const netAnnual  = grossTotal - totalTax
    const netMonthly = netAnnual / 12

    const housing  = totalMonthly || 0
    const food     = (foodWeekly || 0) * (52 / 12)
    const cars     = carPayments  || 0
    const health   = healthIns    || 0
    const utils    = utilities    || 0
    const subs     = subscriptions|| 0
    const vacation = (vacationAnnual || 0) / 12
    const other    = otherMonthly || 0
    const totalExpenses = housing + food + cars + health + utils + subs + vacation + other
    const monthlyLeft   = netMonthly - totalExpenses
    const weeklyLeft    = monthlyLeft / 4.33
    const annualLeft    = monthlyLeft * 12
    const housingRatio  = netMonthly > 0 ? (housing / netMonthly) * 100 : 0

    // Lender max home price (gross-income based, standard DTI)
    const moGross      = grossTotal / 12
    const maxFront     = moGross * (frontRatio / 100)
    const maxBack      = moGross * (backRatio  / 100) - cars
    const maxPayment   = Math.max(0, Math.min(maxFront, maxBack))
    const piPayment    = maxPayment * 0.85
    const r            = (rate      || 7)  / 100 / 12
    const n            = (termYears || 30) * 12
    const maxLoan      = r > 0 ? piPayment * (Math.pow(1+r,n)-1) / (r * Math.pow(1+r,n)) : piPayment * n
    const maxPrice     = maxLoan / (1 - (downPct || 20) / 100)

    return {
      grossTotal, gross1, gross2,
      federalTax, ficaTotal, stateTax, stateRate, stateKey, totalTax,
      netAnnual, netMonthly,
      housing, food, cars, health, utils, subs, vacation, other, totalExpenses,
      monthlyLeft, weeklyLeft, annualLeft, housingRatio,
      maxPayment, maxLoan, maxPrice,
    }
  }, [salary1,extra1,bonus1,hasCo,salary2,extra2,bonus2,filing,taxState,
      totalMonthly,foodWeekly,carPayments,healthIns,utilities,subscriptions,
      vacationAnnual,otherMonthly,frontRatio,backRatio,rate,termYears,downPct])

  return (
    <div className="space-y-6">

      {/* Income */}
      <div>
        <p className="text-xs font-semibold text-ink-muted uppercase tracking-wide mb-3">Income</p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <NumberInput label="Salary (annual)" value={salary1} onChange={setSalary1} prefix="$" step={1000} placeholder="80,000" />
          <NumberInput label="Other income / side job" value={extra1} onChange={setExtra1} prefix="$" step={500} placeholder="0" hint="Annual total" />
          <NumberInput label="Annual bonus" value={bonus1} onChange={setBonus1} prefix="$" step={500} placeholder="0" />
        </div>
        {hasCo && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3 pt-3 border-t border-canvas-700">
            <NumberInput label="Co-borrower salary" value={salary2} onChange={setSalary2} prefix="$" step={1000} placeholder="60,000" />
            <NumberInput label="Co-borrower other income" value={extra2} onChange={setExtra2} prefix="$" step={500} placeholder="0" hint="Annual total" />
            <NumberInput label="Co-borrower bonus" value={bonus2} onChange={setBonus2} prefix="$" step={500} placeholder="0" />
          </div>
        )}
        <button
          onClick={() => setHasCo(v => !v)}
          className="mt-3 text-xs text-amber-400/80 hover:text-amber-400 transition-colors"
        >
          {hasCo ? '− Remove co-borrower' : '+ Add co-borrower / spouse'}
        </button>
      </div>

      {/* Tax settings */}
      <div>
        <p className="text-xs font-semibold text-ink-muted uppercase tracking-wide mb-3">Tax Settings <span className="normal-case font-normal text-ink-muted/60">(2024 federal brackets)</span></p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="block text-xs font-medium text-ink-muted">State of residence</label>
            <select
              value={taxState}
              onChange={e => setTaxState(e.target.value)}
              className="w-full bg-canvas-800 border border-canvas-600 rounded-lg py-2.5 px-3 text-sm text-ink-base focus:border-amber-500 focus:outline-none"
            >
              <option value="">— Select state —</option>
              {US_STATES.map(([code, name]) => (
                <option key={code} value={code}>{name} ({code})</option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label className="block text-xs font-medium text-ink-muted">Filing status</label>
            <select
              value={filing}
              onChange={e => setFiling(e.target.value)}
              className="w-full bg-canvas-800 border border-canvas-600 rounded-lg py-2.5 px-3 text-sm text-ink-base focus:border-amber-500 focus:outline-none"
            >
              <option value="single">Single</option>
              <option value="mfj">Married Filing Jointly</option>
            </select>
          </div>
        </div>
        {calcs && (
          <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2">
            {[
              { label: 'Federal tax',   v: calcs.federalTax, pct: (calcs.federalTax/calcs.grossTotal*100).toFixed(1), color: 'text-red-400' },
              { label: 'FICA (SS+Med)', v: calcs.ficaTotal,  pct: (calcs.ficaTotal /calcs.grossTotal*100).toFixed(1), color: 'text-orange-400' },
              { label: `State (${calcs.stateKey || '—'})`, v: calcs.stateTax, pct: calcs.stateRate != null ? calcs.stateRate.toFixed(1) : null, color: 'text-yellow-400', noRate: calcs.stateRate === null && !taxState },
              { label: 'Net annual',    v: calcs.netAnnual,  pct: null, color: 'text-match-strong' },
            ].map(item => (
              <div key={item.label} className="bg-canvas-800 border border-canvas-600 rounded-lg p-2.5 text-center">
                <p className="text-xs text-ink-muted mb-0.5">{item.label}</p>
                {item.noRate ? (
                  <p className="text-xs text-ink-muted italic">select state</p>
                ) : (
                  <>
                    <p className={`text-sm font-bold font-mono ${item.color}`}>{fmt(item.v, true)}</p>
                    {item.pct != null && <p className="text-xs text-ink-muted">{item.pct}% eff. rate</p>}
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Monthly expenses */}
      <div>
        <p className="text-xs font-semibold text-ink-muted uppercase tracking-wide mb-3">Monthly Expenses</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {(totalMonthly || 0) > 0 && (
            <div className="space-y-1 sm:col-span-2">
              <label className="block text-xs font-medium text-ink-muted">Housing payment (from calculator)</label>
              <div className="bg-canvas-800 border border-amber-500/30 rounded-lg py-2.5 px-3 text-sm text-amber-400 font-mono font-semibold">{fmt(totalMonthly)}/mo — PITI + HOA</div>
            </div>
          )}
          <NumberInput label="Groceries / food" value={foodWeekly} onChange={setFoodWeekly} prefix="$" suffix="/ wk" step={25} placeholder="200" hint={foodWeekly ? `≈ ${fmt((foodWeekly||0)*(52/12))}/mo` : 'Per week → auto-converts'} />
          <NumberInput label="Car payments" value={carPayments} onChange={setCarPayments} prefix="$" suffix="/ mo" step={50} placeholder="0" hint="All vehicles combined" />
          <NumberInput label="Health insurance" value={healthIns} onChange={setHealthIns} prefix="$" suffix="/ mo" step={25} placeholder="0" hint="After employer contribution" />
          <NumberInput label="Utilities" value={utilities} onChange={setUtilities} prefix="$" suffix="/ mo" step={25} placeholder="200" hint="Electric, gas, water, internet" />
          <NumberInput label="Subscriptions" value={subscriptions} onChange={setSubscriptions} prefix="$" suffix="/ mo" step={5} placeholder="0" hint="Streaming, software, gym…" />
          <NumberInput label="Vacations / travel" value={vacationAnnual} onChange={setVacationAnnual} prefix="$" suffix="/ yr" step={250} placeholder="0" hint={vacationAnnual ? `≈ ${fmt((vacationAnnual||0)/12)}/mo` : 'Annual total → monthly'} />
          <NumberInput label="Other / misc" value={otherMonthly} onChange={setOtherMonthly} prefix="$" suffix="/ mo" step={50} placeholder="0" hint="Dining out, clothing, etc." />
        </div>
      </div>

      {/* Results */}
      {calcs ? (
        <div className="space-y-3">
          <p className="text-xs font-semibold text-ink-muted uppercase tracking-wide">Budget Summary</p>

          {/* Leftover hero */}
          <div className={`rounded-2xl p-5 border ${
            calcs.monthlyLeft >= 1000 ? 'bg-match-strong/10 border-match-strong/30'
            : calcs.monthlyLeft >= 0  ? 'bg-amber-500/10  border-amber-500/30'
            : 'bg-red-500/10 border-red-500/30'
          }`}>
            <p className="text-xs text-ink-muted mb-1">Monthly leftover after all expenses &amp; taxes</p>
            <p className={`text-4xl font-bold font-mono ${
              calcs.monthlyLeft >= 1000 ? 'text-match-strong'
              : calcs.monthlyLeft >= 0  ? 'text-amber-400'
              : 'text-red-400'
            }`}>{fmt(calcs.monthlyLeft)}<span className="text-lg font-normal text-ink-muted"> /mo</span></p>
            <div className="flex gap-5 mt-2 flex-wrap">
              <span className="text-sm text-ink-muted">{fmt(calcs.weeklyLeft)}<span className="text-xs opacity-60 ml-0.5">/wk</span></span>
              <span className="text-sm text-ink-muted">{fmt(calcs.annualLeft, true)}<span className="text-xs opacity-60 ml-0.5">/yr</span></span>
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                calcs.housingRatio <= 28 ? 'bg-match-strong/15 text-match-strong'
                : calcs.housingRatio <= 36 ? 'bg-amber-500/15 text-amber-400'
                : 'bg-red-500/15 text-red-400'
              }`}>Housing {calcs.housingRatio.toFixed(0)}% of net</span>
            </div>
          </div>

          {/* Line-by-line breakdown */}
          <div className="bg-canvas-900 border border-canvas-700 rounded-xl p-4 space-y-1.5 text-sm">
            {[
              { label: 'Net monthly income',    value: calcs.netMonthly,    cls: 'text-match-strong font-semibold' },
              { label: '− Housing (PITI+HOA)',  value: calcs.housing,       cls: 'text-red-400/80', show: calcs.housing > 0 },
              { label: '− Groceries',           value: calcs.food,          cls: 'text-ink-muted',  show: calcs.food > 0 },
              { label: '− Car payments',        value: calcs.cars,          cls: 'text-ink-muted',  show: calcs.cars > 0 },
              { label: '− Health insurance',    value: calcs.health,        cls: 'text-ink-muted',  show: calcs.health > 0 },
              { label: '− Utilities',           value: calcs.utils,         cls: 'text-ink-muted',  show: calcs.utils > 0 },
              { label: '− Subscriptions',       value: calcs.subs,          cls: 'text-ink-muted',  show: calcs.subs > 0 },
              { label: '− Vacation (monthly)',  value: calcs.vacation,      cls: 'text-ink-muted',  show: calcs.vacation > 0 },
              { label: '− Other',               value: calcs.other,         cls: 'text-ink-muted',  show: calcs.other > 0 },
              { label: '= Remaining',           value: calcs.monthlyLeft,   cls: calcs.monthlyLeft >= 0 ? 'text-match-strong font-semibold' : 'text-red-400 font-semibold', border: true },
            ].filter(r => r.show !== false).map(row => (
              <div key={row.label} className={`flex justify-between items-baseline ${row.border ? 'border-t border-canvas-700 pt-2 mt-2' : ''}`}>
                <span className="text-ink-muted">{row.label}</span>
                <span className={`font-mono ${row.cls}`}>{fmt(Math.abs(row.value))}</span>
              </div>
            ))}
          </div>

          {/* Lender qualification */}
          <div className="bg-canvas-900 border border-canvas-700 rounded-xl p-4 space-y-3">
            <p className="text-xs font-semibold text-ink-muted">Lender Qualification <span className="font-normal">(based on gross income + DTI ratios)</span></p>
            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="bg-canvas-800 rounded-lg p-3">
                <p className="text-xs text-ink-muted mb-0.5">Max home price</p>
                <p className="text-xl font-bold text-amber-400 font-mono">{fmt(calcs.maxPrice, true)}</p>
              </div>
              <div className="bg-canvas-800 rounded-lg p-3">
                <p className="text-xs text-ink-muted mb-0.5">Max loan</p>
                <p className="text-lg font-bold text-ink-base font-mono">{fmt(calcs.maxLoan, true)}</p>
              </div>
              <div className="bg-canvas-800 rounded-lg p-3">
                <p className="text-xs text-ink-muted mb-0.5">Max payment</p>
                <p className="text-lg font-bold text-ink-base font-mono">{fmt(calcs.maxPayment)}/mo</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <NumberInput label="Front-end ratio (housing)" value={frontRatio} onChange={setFrontRatio} suffix="%" min={20} max={40} step={1} hint="28% typical" />
              <NumberInput label="Back-end ratio (all debt)" value={backRatio} onChange={setBackRatio} suffix="%" min={28} max={50} step={1} hint="36–43% typical" />
            </div>
          </div>
        </div>
      ) : (
        <p className="text-sm text-ink-muted">Enter at least one income amount above to see your full budget breakdown.</p>
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

// --- Income tax helpers ---

// Approximate effective state income tax rates (%) at ~$100K gross income
const STATE_INCOME_TAX_RATES = {
  AK: 0, FL: 0, NV: 0, NH: 0, SD: 0, TN: 0, TX: 0, WA: 0, WY: 0,   // no income tax
  CO: 4.40, IL: 4.95, IN: 3.15, KY: 4.50, MA: 5.00, MI: 4.25,        // flat tax
  NC: 4.75, PA: 3.07, UT: 4.65,
  AL: 3.50, AR: 3.80, AZ: 2.50, CA: 6.50, CT: 5.00, DC: 6.50, DE: 5.20, GA: 5.49,
  HI: 8.25, IA: 4.70, ID: 5.80, KS: 4.80, LA: 3.50, MD: 4.90, ME: 6.50, MN: 6.80,
  MO: 4.50, MS: 4.00, MT: 5.90, NE: 5.20, NJ: 4.50, NM: 4.70, NY: 6.10, ND: 1.40,
  OH: 3.50, OK: 3.50, OR: 7.80, RI: 4.80, SC: 5.50, VA: 5.50, VT: 5.90, WV: 4.50, WI: 5.50,
}

// 2024 federal tax brackets [upper bound, marginal rate]
const FED_BRACKETS = {
  single: [[11600,0.10],[47150,0.12],[100525,0.22],[191950,0.24],[243725,0.32],[609350,0.35],[Infinity,0.37]],
  mfj:    [[23200,0.10],[94300,0.12],[201050,0.22],[383900,0.24],[487450,0.32],[731200,0.35],[Infinity,0.37]],
}
const STD_DEDUCTION = { single: 14600, mfj: 29200 }

function calcFederalTax(gross, filing) {
  const brackets = FED_BRACKETS[filing] || FED_BRACKETS.single
  let taxable = Math.max(0, gross - (STD_DEDUCTION[filing] || 14600))
  let tax = 0, prev = 0
  for (const [top, rate] of brackets) {
    if (taxable <= 0) break
    const chunk = Math.min(taxable, top - prev)
    tax += chunk * rate; taxable -= chunk; prev = top
  }
  return tax
}

// FICA per person: SS 6.2% up to $168,600 + Medicare 1.45%
function calcFICA(wages) {
  return Math.min(wages, 168600) * 0.062 + wages * 0.0145
}

const US_STATES = [
  ['AL','Alabama'],['AK','Alaska'],['AZ','Arizona'],['AR','Arkansas'],['CA','California'],
  ['CO','Colorado'],['CT','Connecticut'],['DC','Washington DC'],['DE','Delaware'],
  ['FL','Florida'],['GA','Georgia'],['HI','Hawaii'],['ID','Idaho'],['IL','Illinois'],
  ['IN','Indiana'],['IA','Iowa'],['KS','Kansas'],['KY','Kentucky'],['LA','Louisiana'],
  ['ME','Maine'],['MD','Maryland'],['MA','Massachusetts'],['MI','Michigan'],['MN','Minnesota'],
  ['MS','Mississippi'],['MO','Missouri'],['MT','Montana'],['NE','Nebraska'],['NV','Nevada'],
  ['NH','New Hampshire'],['NJ','New Jersey'],['NM','New Mexico'],['NY','New York'],
  ['NC','North Carolina'],['ND','North Dakota'],['OH','Ohio'],['OK','Oklahoma'],['OR','Oregon'],
  ['PA','Pennsylvania'],['RI','Rhode Island'],['SC','South Carolina'],['SD','South Dakota'],
  ['TN','Tennessee'],['TX','Texas'],['UT','Utah'],['VT','Vermont'],['VA','Virginia'],
  ['WA','Washington'],['WV','West Virginia'],['WI','Wisconsin'],['WY','Wyoming'],
]

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
              <AffordabilityCalc rate={rate} termYears={termYears} downPct={downPct} totalMonthly={totalMonthly} seedState={seedState} />
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
