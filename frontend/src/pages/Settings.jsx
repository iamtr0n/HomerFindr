import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'
import { Save, Loader2, CheckCircle, XCircle, FlaskConical, Webhook, Mail, Clock, Copy, Check, Plus, Trash2, Radio, MapPin, Sparkles, ShieldCheck, Terminal } from 'lucide-react'
import { Button } from '../components/ui/Button'

function Section({ icon: Icon, title, children }) {
  return (
    <div className="bg-canvas-900 border border-canvas-700 rounded-xl overflow-hidden">
      <div className="flex items-center gap-2.5 px-5 py-3.5 border-b border-canvas-700">
        <Icon size={16} className="text-amber-400" />
        <h2 className="font-semibold text-sm text-ink-primary">{title}</h2>
      </div>
      <div className="p-5 space-y-4">{children}</div>
    </div>
  )
}

function Field({ label, hint, children }) {
  return (
    <div>
      <label className="block text-xs text-ink-muted uppercase tracking-widest font-medium mb-1.5">{label}</label>
      {children}
      {hint && <p className="text-xs text-ink-muted mt-1">{hint}</p>}
    </div>
  )
}

const inputCls = 'w-full px-3 py-2 text-sm bg-canvas-800 border border-canvas-600 rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:border-amber-500 transition-colors'

const CARRIERS = {
  verizon: { label: 'Verizon',   gateway: '@vtext.com' },
  att:     { label: 'AT&T',      gateway: '@txt.att.net' },
  tmobile: { label: 'T-Mobile',  gateway: '@tmomail.net' },
  sprint:  { label: 'Sprint',    gateway: '@messaging.sprintpcs.com' },
  metro:   { label: 'Metro PCS', gateway: '@mymetropcs.com' },
  cricket: { label: 'Cricket',   gateway: '@sms.cricketwireless.net' },
  boost:   { label: 'Boost',     gateway: '@sms.myboostmobile.com' },
}

function toGatewayEmail(number, carrier) {
  const digits = number.replace(/\D/g, '')
  const gw = CARRIERS[carrier]?.gateway || '@vtext.com'
  return digits.length >= 10 ? digits + gw : null
}

function buildZapierPrompt(phones) {
  const recipients = phones
    .filter(p => p.number && p.number.replace(/\D/g, '').length >= 10)
    .map(p => toGatewayEmail(p.number, p.carrier))
    .filter(Boolean)

  const toLine = recipients.length > 0
    ? recipients.join(', ')
    : '[add phone numbers with carrier above]'

  const emailSteps = (path) => recipients.length === 0
    ? ['- Email by Zapier → Send Outbound Email\n  - To: [gateway email]\n' + path]
    : recipients.map(addr => '- Email by Zapier → Send Outbound Email\n  - To: ' + addr + '\n' + path)

  const emailPath = [
    '  - Subject: (leave blank)',
    '  - Body (plain text):',
    '    {{message}}',
    '  NOTE: The {{message}} field is pre-formatted and already includes:',
    '  address, price, beds/baths, sqft, Realtor.com link,',
    '  and "Reply STOP to opt out · Reply ADD [number] to add a contact"',
  ].join('\n')

  const lines = [
    'Build a Zap with these exact steps:',
    '',
    'TRIGGER:',
    '- Webhooks by Zapier → Catch Raw Hook',
    '- Copy the webhook URL and paste it into HomerFindr Settings → Global Zapier Webhook',
    '',
    'ACTION (send as SMS via carrier email gateway):',
    '- Email by Zapier → Send Outbound Email',
    `- To: ${toLine}`,
    ...emailPath.split('\n'),
    '',
    '---',
    'NOTES:',
    '- Use "Email by Zapier" only — free, no account needed, sends as SMS via carrier gateway',
    '- Do NOT use Twilio, Happy SMS, or any paid/third-party SMS app',
    '- Map ONLY the {{message}} field to the body — it contains everything',
    '- Leave subject blank — carrier gateways ignore it',
    recipients.length > 0 ? '- Recipients: ' + toLine : '- Add phone numbers above to populate recipients',
    '- Reply STOP and Reply ADD instructions are already in every message',
  ]
  return lines.join('\n')
}


export default function Settings() {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['settings'], queryFn: api.getSettings })

  const [smtp, setSmtp] = useState(null)
  const [webhook, setWebhook] = useState(null)
  const [schedule, setSchedule] = useState(null)
  const [testResult, setTestResult] = useState(null)
  const [webhookTestResult, setWebhookTestResult] = useState(null)
  const webhookTestMutation = useMutation({
    mutationFn: () => api.testWebhook(),
    onSuccess: (result) => setWebhookTestResult(result),
  })
  const [phones, setPhones] = useState([{ number: '', carrier: 'verizon' }])
  const [promptGenerated, setPromptGenerated] = useState(false)
  const [generatedPrompt, setGeneratedPrompt] = useState('')
  const [copied, setCopied] = useState(false)
  const [editingWebhook, setEditingWebhook] = useState(false)

  const smtpForm = smtp ?? {
    smtp_host: data?.smtp_host ?? 'smtp.gmail.com',
    smtp_port: data?.smtp_port ?? 587,
    smtp_user: data?.smtp_user ?? '',
    smtp_password: '',
    report_email: data?.report_email ?? '',
  }
  const webhookForm = webhook ?? { zapier_webhook_url: data?.zapier_webhook_url ?? '' }
  const savedWebhookUrl = data?.zapier_webhook_url ?? ''
  const scheduleForm = schedule ?? {
    report_hour: data?.report_hour ?? 7,
    report_minute: data?.report_minute ?? 0,
  }

  const schedulerQuery = useQuery({ queryKey: ['scheduler'], queryFn: api.getSchedulerSettings })
  const [schedulerForm, setSchedulerForm] = useState(null)
  useEffect(() => {
    if (schedulerQuery.data && !schedulerForm) {
      const tz = schedulerQuery.data.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone
      setSchedulerForm({ enabled: schedulerQuery.data.enabled, interval_minutes: schedulerQuery.data.interval_minutes, timezone: tz })
    }
  }, [schedulerQuery.data])
  const schedulerMutation = useMutation({
    mutationFn: (d) => api.updateSchedulerSettings(d),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['scheduler'] }),
  })

  const [cliLaunched, setCliLaunched] = useState(null) // null | 'ok' | 'err'
  const [aiKey, setAiKey] = useState('')
  const [openaiKey, setOpenaiKey] = useState('')
  const [googleKey, setGoogleKey] = useState('')
  const aiKeySet = data?.anthropic_api_key_set ?? false

  const [workAddress, setWorkAddress] = useState(data?.work_address ?? '')
  const workGeocoded = !!(data?.work_lat)

  const saveWorkMutation = useMutation({
    mutationFn: (payload) => api.updateSettings(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['settings'] }),
  })

  const saveMutation = useMutation({
    mutationFn: (payload) => api.updateSettings(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      queryClient.invalidateQueries({ queryKey: ['settings-status'] })
    },
  })

  const testMutation = useMutation({
    mutationFn: async () => {
      // Save SMTP first, then test
      await api.updateSettings({
        smtp_host: smtpForm.smtp_host,
        smtp_port: Number(smtpForm.smtp_port),
        smtp_user: smtpForm.smtp_user,
        smtp_password: smtpForm.smtp_password || undefined,
        report_email: smtpForm.report_email,
      })
      return api.testSmtp()
    },
    onSuccess: (result) => setTestResult(result),
  })

  if (isLoading) return (
    <div className="flex justify-center py-20">
      <Loader2 size={32} className="animate-spin text-amber-500" />
    </div>
  )

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="mb-2">
        <h1 className="font-serif text-2xl text-ink-primary">Settings</h1>
        {data?.env_file && (
          <p className="text-xs text-ink-muted mt-1">
            Saved to: <code className="text-amber-400/80 bg-canvas-800 px-1.5 py-0.5 rounded">{data.env_file}</code>
          </p>
        )}
      </div>

      {/* AI Offer Analysis */}
      <Section icon={Sparkles} title="AI Offer Analysis">
        <p className="text-xs text-ink-muted -mt-1">
          Powers the CMA narrative, photo condition assessment, and neighborhood context on listing cards.
          Add one or more provider keys — HomerFindr uses the first configured one.
        </p>
        <div className="flex items-center gap-2 text-xs text-ink-muted bg-canvas-800 border border-canvas-700 rounded-lg px-3 py-2">
          <ShieldCheck size={13} className="text-match-strong shrink-0" />
          Keys are stored in your local <code className="text-amber-400/80">.env</code> file only — they are never sent to your browser or any third party.
        </div>

        {/* Anthropic */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-ink-muted uppercase tracking-widest">Anthropic (Claude)</label>
            {aiKeySet
              ? <span className="flex items-center gap-1 text-xs text-match-strong"><CheckCircle size={11} /> Configured</span>
              : <span className="flex items-center gap-1 text-xs text-ink-muted"><XCircle size={11} /> Not set</span>
            }
          </div>
          <div className="flex gap-2">
            <input
              type="password"
              value={aiKey}
              onChange={e => setAiKey(e.target.value)}
              placeholder={aiKeySet ? '••••••••••••••••••••••••' : 'sk-ant-api03-...'}
              className={inputCls}
              autoComplete="off"
            />
            <Button
              size="sm"
              onClick={() => saveMutation.mutate({ anthropic_api_key: aiKey })}
              disabled={!aiKey || saveMutation.isPending}
            >
              {saveMutation.isPending ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
              Save
            </Button>
          </div>
          <p className="text-xs text-ink-muted">Get a key at <span className="text-amber-400/80">console.anthropic.com</span> · Recommended: claude-sonnet-4-6</p>
        </div>

        {/* OpenAI */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-ink-muted uppercase tracking-widest">OpenAI (GPT-4o)</label>
            {data?.openai_api_key_set
              ? <span className="flex items-center gap-1 text-xs text-match-strong"><CheckCircle size={11} /> Configured</span>
              : <span className="flex items-center gap-1 text-xs text-ink-muted"><XCircle size={11} /> Not set</span>
            }
          </div>
          <div className="flex gap-2">
            <input
              type="password"
              value={openaiKey}
              onChange={e => setOpenaiKey(e.target.value)}
              placeholder={data?.openai_api_key_set ? '••••••••••••••••••••••••' : 'sk-proj-...'}
              className={inputCls}
              autoComplete="off"
            />
            <Button
              size="sm"
              onClick={() => saveMutation.mutate({ openai_api_key: openaiKey })}
              disabled={!openaiKey || saveMutation.isPending}
            >
              {saveMutation.isPending ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
              Save
            </Button>
          </div>
          <p className="text-xs text-ink-muted">Get a key at <span className="text-amber-400/80">platform.openai.com</span> · Supports vision + web browsing</p>
        </div>

        {/* Google Gemini */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-ink-muted uppercase tracking-widest">Google Gemini</label>
            {data?.google_api_key_set
              ? <span className="flex items-center gap-1 text-xs text-match-strong"><CheckCircle size={11} /> Configured</span>
              : <span className="flex items-center gap-1 text-xs text-ink-muted"><XCircle size={11} /> Not set</span>
            }
          </div>
          <div className="flex gap-2">
            <input
              type="password"
              value={googleKey}
              onChange={e => setGoogleKey(e.target.value)}
              placeholder={data?.google_api_key_set ? '••••••••••••••••••••••••' : 'AIza...'}
              className={inputCls}
              autoComplete="off"
            />
            <Button
              size="sm"
              onClick={() => saveMutation.mutate({ google_api_key: googleKey })}
              disabled={!googleKey || saveMutation.isPending}
            >
              {saveMutation.isPending ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
              Save
            </Button>
          </div>
          <p className="text-xs text-ink-muted">Get a key at <span className="text-amber-400/80">aistudio.google.com</span> · Has Google Search grounding</p>
        </div>
      </Section>

      {/* CLI Access */}
      <Section icon={Terminal} title="CLI Access">
        <p className="text-xs text-ink-muted -mt-1">
          Launch the interactive search wizard directly from your terminal.
          The button opens a new terminal window and starts <code className="text-amber-400/80">homesearch</code>.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-2">
            <p className="text-xs font-medium text-ink-muted uppercase tracking-widest">macOS</p>
            <Button
              variant="default"
              size="sm"
              className="w-full"
              onClick={() => api.openCli().then(() => setCliLaunched('ok')).catch(() => setCliLaunched('err'))}
            >
              <Terminal size={13} />
              Open in Terminal
            </Button>
            <p className="text-xs text-ink-muted font-mono bg-canvas-800 border border-canvas-700 rounded px-2 py-1.5 select-all">homesearch</p>
          </div>
          <div className="space-y-2">
            <p className="text-xs font-medium text-ink-muted uppercase tracking-widest">Windows</p>
            <Button
              variant="default"
              size="sm"
              className="w-full"
              onClick={() => api.openCli().then(() => setCliLaunched('ok')).catch(() => setCliLaunched('err'))}
            >
              <Terminal size={13} />
              Open in CMD
            </Button>
            <p className="text-xs text-ink-muted font-mono bg-canvas-800 border border-canvas-700 rounded px-2 py-1.5 select-all">homesearch</p>
          </div>
        </div>
        {cliLaunched === 'ok' && <p className="text-xs text-match-strong">✓ Terminal opened — check your taskbar if it's not in front</p>}
        {cliLaunched === 'err' && <p className="text-xs text-red-400">Could not open terminal automatically — run <code className="font-mono">homesearch</code> manually</p>}
        <p className="text-xs text-ink-muted">
          Or install first: <code className="text-amber-400/80">pip install homefindr</code> · then run <code className="text-amber-400/80">homesearch</code>
        </p>
      </Section>

      {/* Background Monitor */}
      <Section icon={Radio} title="Background Monitor">
        {schedulerForm ? (
          <>
            <div className="flex items-center gap-2 -mt-1 mb-3">
              <div className={`w-2 h-2 rounded-full ${schedulerForm.enabled ? 'bg-match-strong animate-pulse' : 'bg-canvas-500'}`} />
              <p className="text-xs text-ink-muted">
                {schedulerForm.enabled
                  ? `Checking every ${schedulerForm.interval_minutes} min — new listings appear automatically`
                  : 'Paused — searches run manually only'}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-4">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <div
                  onClick={() => setSchedulerForm(f => ({ ...f, enabled: !f.enabled }))}
                  className={`w-10 h-5 rounded-full transition-colors relative cursor-pointer ${schedulerForm.enabled ? 'bg-match-strong' : 'bg-canvas-600'}`}
                >
                  <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${schedulerForm.enabled ? 'translate-x-5' : 'translate-x-0.5'}`} />
                </div>
                <span className="text-sm text-ink-secondary">{schedulerForm.enabled ? 'Enabled' : 'Disabled'}</span>
              </label>
              <div className="flex items-center gap-2">
                <span className="text-xs text-ink-muted">Check every</span>
                <select
                  value={schedulerForm.interval_minutes}
                  onChange={(e) => setSchedulerForm(f => ({ ...f, interval_minutes: +e.target.value }))}
                  className="py-1 px-2 bg-canvas-800 border border-canvas-600 rounded-lg text-xs text-ink-secondary focus:border-amber-500 focus:outline-none"
                >
                  {[1, 2, 3, 5, 10, 15, 30].map(n => <option key={n} value={n}>{n} min</option>)}
                </select>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-ink-muted">Timezone</span>
                <input
                  value={schedulerForm.timezone}
                  onChange={(e) => setSchedulerForm(f => ({ ...f, timezone: e.target.value }))}
                  className="w-44 py-1 px-2 bg-canvas-800 border border-canvas-600 rounded-lg text-xs text-ink-secondary focus:border-amber-500 focus:outline-none"
                  placeholder="America/New_York"
                />
              </div>
              <Button size="sm" onClick={() => schedulerMutation.mutate(schedulerForm)} disabled={schedulerMutation.isPending}>
                {schedulerMutation.isPending ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
                Save
              </Button>
              {schedulerMutation.isSuccess && <span className="text-xs text-match-strong">Saved ✓</span>}
            </div>
          </>
        ) : (
          <div className="flex justify-center py-4"><Loader2 size={20} className="animate-spin text-amber-500" /></div>
        )}
      </Section>

      {/* Commute */}
      <Section icon={MapPin} title="Commute">
        <Field label="Work Address" hint="Used to estimate commute time on each listing card">
          <input
            className={inputCls}
            value={workAddress}
            onChange={e => setWorkAddress(e.target.value)}
            placeholder="123 Main St, New York, NY"
          />
        </Field>
        {workGeocoded && (
          <p className="text-xs text-match-strong">✓ Location found</p>
        )}
        <div className="flex gap-2 pt-1">
          <Button variant="default" size="sm" onClick={() => saveWorkMutation.mutate({ work_address: workAddress })} disabled={saveWorkMutation.isPending}>
            {saveWorkMutation.isPending ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
            Save
          </Button>
          {saveWorkMutation.isSuccess && <span className="text-xs text-match-strong self-center">Saved ✓</span>}
        </div>
      </Section>

      {/* Email / SMTP */}
      <Section icon={Mail} title="Email Reports">
        <div className="grid grid-cols-2 gap-3">
          <Field label="SMTP Host">
            <input className={inputCls} value={smtpForm.smtp_host} onChange={e => setSmtp(f => ({ ...smtpForm, smtp_host: e.target.value }))} placeholder="smtp.gmail.com" />
          </Field>
          <Field label="SMTP Port">
            <input className={inputCls} type="number" value={smtpForm.smtp_port} onChange={e => setSmtp({ ...smtpForm, smtp_port: Number(e.target.value) })} placeholder="587" />
          </Field>
        </div>
        <Field label="SMTP Username" hint="Your email address (used to log in to the SMTP server)">
          <input className={inputCls} value={smtpForm.smtp_user} onChange={e => setSmtp({ ...smtpForm, smtp_user: e.target.value })} placeholder="you@gmail.com" />
        </Field>
        <Field label="SMTP Password" hint={data?.smtp_password_set ? 'Password is set — leave blank to keep unchanged' : 'For Gmail, use an App Password (not your login password)'}>
          <input className={inputCls} type="password" value={smtpForm.smtp_password} onChange={e => setSmtp({ ...smtpForm, smtp_password: e.target.value })} placeholder={data?.smtp_password_set ? '••••••••' : 'App password'} />
        </Field>
        <Field label="Report Recipient Email" hint="Where the daily report is sent">
          <input className={inputCls} value={smtpForm.report_email} onChange={e => setSmtp({ ...smtpForm, report_email: e.target.value })} placeholder="recipient@email.com" />
        </Field>

        {testResult && (
          <div className={`flex items-start gap-2.5 rounded-lg px-3.5 py-2.5 text-sm border ${testResult.success ? 'bg-match-strong/10 border-match-strong/30 text-match-strong' : 'bg-red-500/10 border-red-500/30 text-red-400'}`}>
            {testResult.success ? <CheckCircle size={15} className="shrink-0 mt-0.5" /> : <XCircle size={15} className="shrink-0 mt-0.5" />}
            {testResult.message}
          </div>
        )}

        <div className="flex gap-2 pt-1">
          <Button
            variant="outline"
            size="sm"
            onClick={() => { setTestResult(null); testMutation.mutate() }}
            disabled={testMutation.isPending}
          >
            {testMutation.isPending ? <Loader2 size={13} className="animate-spin" /> : <FlaskConical size={13} />}
            Test Connection
          </Button>
          <Button
            variant="default"
            size="sm"
            onClick={() => saveMutation.mutate({
              smtp_host: smtpForm.smtp_host,
              smtp_port: Number(smtpForm.smtp_port),
              smtp_user: smtpForm.smtp_user,
              smtp_password: smtpForm.smtp_password || undefined,
              report_email: smtpForm.report_email,
            })}
            disabled={saveMutation.isPending}
          >
            {saveMutation.isPending ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
            Save
          </Button>
          {saveMutation.isSuccess && <span className="text-xs text-match-strong self-center">Saved ✓{saveMutation.data?.restart_required ? ' — restart server to apply' : ''}</span>}
        </div>
      </Section>

      {/* Report Schedule */}
      <Section icon={Clock} title="Report Schedule">
        <p className="text-xs text-ink-muted -mt-1">Daily digest and email report time</p>
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={scheduleForm.report_hour % 12 === 0 ? 12 : scheduleForm.report_hour % 12}
            onChange={e => {
              const h12 = Number(e.target.value)
              const isPm = scheduleForm.report_hour >= 12
              setSchedule({ ...scheduleForm, report_hour: isPm ? (h12 === 12 ? 12 : h12 + 12) : (h12 === 12 ? 0 : h12) })
            }}
            className={inputCls + ' w-24'}
          >
            {[12,1,2,3,4,5,6,7,8,9,10,11].map(h => <option key={h} value={h}>{h}</option>)}
          </select>
          <select
            value={scheduleForm.report_minute}
            onChange={e => setSchedule({ ...scheduleForm, report_minute: Number(e.target.value) })}
            className={inputCls + ' w-24'}
          >
            {[0,15,30,45].map(m => <option key={m} value={m}>{String(m).padStart(2,'0')}</option>)}
          </select>
          <select
            value={scheduleForm.report_hour >= 12 ? 'pm' : 'am'}
            onChange={e => {
              const isPm = e.target.value === 'pm'
              const h12 = scheduleForm.report_hour % 12 === 0 ? 12 : scheduleForm.report_hour % 12
              setSchedule({ ...scheduleForm, report_hour: isPm ? (h12 === 12 ? 12 : h12 + 12) : (h12 === 12 ? 0 : h12) })
            }}
            className={inputCls + ' w-20'}
          >
            <option value="am">AM</option>
            <option value="pm">PM</option>
          </select>
        </div>
        <p className="text-xs text-ink-muted">
          Current: <span className="text-amber-400 font-mono">
            {(() => { const h = scheduleForm.report_hour; const h12 = h % 12 === 0 ? 12 : h % 12; const m = String(scheduleForm.report_minute).padStart(2,'0'); return `${h12}:${m} ${h >= 12 ? 'PM' : 'AM'}` })()}
          </span> daily
        </p>
        <div className="flex gap-2 pt-1">
          <Button
            variant="default"
            size="sm"
            onClick={() => saveMutation.mutate({ report_hour: scheduleForm.report_hour, report_minute: scheduleForm.report_minute })}
            disabled={saveMutation.isPending}
          >
            {saveMutation.isPending ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
            Save
          </Button>
          {saveMutation.isSuccess && !saveMutation.data?.restart_required && <span className="text-xs text-match-strong self-center">Saved ✓</span>}
        </div>
      </Section>

      {/* Global Webhook */}
      <Section icon={Webhook} title="Global Zapier Webhook">
        {savedWebhookUrl && !editingWebhook ? (
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-ink-secondary">Registered Webhook</p>
            <div className="flex items-center gap-2 bg-match-strong/10 border border-match-strong/25 rounded-lg px-3 py-2.5">
              <CheckCircle size={14} className="text-match-strong shrink-0" />
              <code className="text-xs text-ink-secondary truncate flex-1">{savedWebhookUrl}</code>
              <button
                onClick={() => { setEditingWebhook(true); setWebhook({ zapier_webhook_url: savedWebhookUrl }) }}
                className="text-xs text-amber-400 hover:text-amber-300 shrink-0 font-medium ml-2"
              >
                Replace
              </button>
            </div>
          </div>
        ) : (
          <Field label="Webhook URL" hint="Fires for all active saved searches that don't have their own webhook. Leave blank to disable.">
            <input
              className={inputCls}
              value={webhookForm.zapier_webhook_url}
              onChange={e => setWebhook({ zapier_webhook_url: e.target.value })}
              placeholder="https://hooks.zapier.com/hooks/catch/..."
              autoFocus={editingWebhook}
            />
          </Field>
        )}
        <div className="text-xs text-ink-muted space-y-1 bg-canvas-800 rounded-lg p-3">
          <p className="font-medium text-ink-secondary">Webhook payload includes:</p>
          <p>• New listings: address, price, beds/baths, sqft, photo, agent info, listing URL</p>
          <p>• Status changes: sale → pending alerts with days-on-market warning</p>
          <p>• Per-search webhooks (set on each saved search) override this global one</p>
        </div>
        {webhookTestResult && !webhookTestResult.success && (
          <div className="flex items-start gap-2.5 rounded-lg px-3.5 py-2.5 text-sm border bg-red-500/10 border-red-500/30 text-red-400">
            <XCircle size={15} className="shrink-0 mt-0.5" />
            {webhookTestResult.message}
          </div>
        )}
        <div className="flex gap-2 pt-1">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => { setWebhookTestResult(null); webhookTestMutation.mutate() }}
            disabled={webhookTestMutation.isPending || !savedWebhookUrl}
            className={
              webhookTestResult?.success === true
                ? 'bg-match-strong/20 border-match-strong/50 text-match-strong hover:bg-match-strong/30'
                : webhookTestResult?.success === false
                ? 'bg-red-500/20 border-red-500/40 text-red-400 hover:bg-red-500/30'
                : ''
            }
          >
            {webhookTestMutation.isPending
              ? <Loader2 size={13} className="animate-spin" />
              : webhookTestResult?.success === true
              ? <CheckCircle size={13} />
              : webhookTestResult?.success === false
              ? <XCircle size={13} />
              : <FlaskConical size={13} />}
            {webhookTestResult?.success === true ? 'Sent!' : webhookTestResult?.success === false ? 'Failed' : 'Send Alert'}
          </Button>
          {(!savedWebhookUrl || editingWebhook) && (
            <Button
              variant="default"
              size="sm"
              onClick={() => { saveMutation.mutate({ zapier_webhook_url: webhookForm.zapier_webhook_url }); setEditingWebhook(false) }}
              disabled={saveMutation.isPending}
            >
              {saveMutation.isPending ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
              Save
            </Button>
          )}
          {editingWebhook && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => { setEditingWebhook(false); setWebhook(null) }}
            >
              Cancel
            </Button>
          )}
          {saveMutation.isSuccess && <span className="text-xs text-match-strong self-center">Saved ✓</span>}
        </div>
      </Section>

      {/* Zapier AI Setup Assistant */}
      <Section icon={Webhook} title="Zapier AI Setup Assistant">
        <p className="text-xs text-ink-muted -mt-1">Enter the phone numbers you want to receive SMS alerts, then generate a prompt to paste into Zapier AI.</p>

        <div className="space-y-2">
          {phones.map((phone, i) => {
            const gateway = toGatewayEmail(phone.number, phone.carrier)
            return (
              <div key={i} className="space-y-1">
                <div className="flex gap-2">
                  <input
                    className={inputCls}
                    value={phone.number}
                    onChange={e => setPhones(ps => ps.map((p, j) => j === i ? { ...p, number: e.target.value } : p))}
                    placeholder="555-123-4567"
                  />
                  <select
                    value={phone.carrier}
                    onChange={e => setPhones(ps => ps.map((p, j) => j === i ? { ...p, carrier: e.target.value } : p))}
                    className="py-2 px-2 bg-canvas-800 border border-canvas-600 rounded-lg text-xs text-ink-secondary focus:border-amber-500 focus:outline-none shrink-0"
                  >
                    {Object.entries(CARRIERS).map(([key, c]) => (
                      <option key={key} value={key}>{c.label}</option>
                    ))}
                  </select>
                  {phones.length > 1 && (
                    <button onClick={() => setPhones(ps => ps.filter((_, j) => j !== i))} className="p-2 text-ink-muted hover:text-red-400 transition-colors">
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
                {gateway && (
                  <p className="text-xs text-ink-muted font-mono pl-1">→ {gateway}</p>
                )}
              </div>
            )
          })}
          <button
            onClick={() => setPhones(ps => [...ps, { number: '', carrier: 'verizon' }])}
            className="flex items-center gap-1.5 text-xs text-ink-muted hover:text-amber-400 transition-colors"
          >
            <Plus size={13} /> Add phone number
          </button>
        </div>

        <div className="flex gap-2 pt-1">
          <Button
            variant="default"
            size="sm"
            onClick={() => {
              const prompt = buildZapierPrompt(phones)
              setGeneratedPrompt(prompt)
              setPromptGenerated(true)
              setCopied(false)
            }}
          >
            Generate Prompt
          </Button>
        </div>

        {promptGenerated && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-xs text-ink-secondary font-medium">Paste this into Zapier AI →</p>
              <button
                onClick={() => { navigator.clipboard.writeText(generatedPrompt); setCopied(true); setTimeout(() => setCopied(false), 2000) }}
                className="flex items-center gap-1.5 text-xs text-ink-muted hover:text-amber-400 transition-colors"
              >
                {copied ? <Check size={13} className="text-match-strong" /> : <Copy size={13} />}
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <textarea
              readOnly
              value={generatedPrompt}
              className="w-full h-48 px-3 py-2 text-xs bg-canvas-800 border border-canvas-600 rounded-lg text-ink-muted font-mono resize-none focus:outline-none focus:border-amber-500 transition-colors"
            />
          </div>
        )}
      </Section>
    </div>
  )
}
