import { useState } from 'react'
import { MoreVertical, Pencil, RefreshCw } from 'lucide-react'
import type { PeriodBalance } from '../../types'

interface Props {
  balances: PeriodBalance[]
  onEdit: (balance: PeriodBalance) => void
  onRecalculate: (currency: string) => void
}

function formatAmount(value: number): string {
  return value.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function closingColorClass(value: number): string {
  if (value > 0) return 'text-positive'
  if (value < 0) return 'text-negative'
  return 'text-text-muted'
}

function exchangeDisplay(value: number): { text: string; color: string } {
  if (value === 0) return { text: formatAmount(0), color: 'text-text-muted' }
  const sign = value > 0 ? '+' : '-'
  return { text: `${sign}${formatAmount(Math.abs(value))}`, color: 'text-text' }
}

function ActionsMenu({ balance, onEdit, onRecalculate }: {
  balance: PeriodBalance
  onEdit: (balance: PeriodBalance) => void
  onRecalculate: (currency: string) => void
}) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-1 text-text-muted hover:text-text hover:bg-surface-hover rounded-none transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
        title="Actions"
      >
        <MoreVertical size={14} strokeWidth={1.5} />
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-dropdown"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full mt-1 right-0 w-52 bg-surface border border-border rounded-sm py-1 z-dropdown">
            <button
              onClick={() => {
                setIsOpen(false)
                onEdit(balance)
              }}
              className="w-full flex items-center gap-2.5 px-3 h-8 text-left text-[13px] text-text hover:bg-surface-hover transition-colors"
            >
              <Pencil size={14} />
              Edit Opening Balance
            </button>
            <button
              onClick={() => {
                setIsOpen(false)
                onRecalculate(balance.currency)
              }}
              className="w-full flex items-center gap-2.5 px-3 h-8 text-left text-[13px] text-text hover:bg-surface-hover transition-colors"
            >
              <RefreshCw size={14} />
              Recalculate
            </button>

            {balance.last_calculated_at && (
              <>
                <div className="h-px bg-border my-1 mx-2" />
                <div className="px-3 py-1.5">
                  <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted">
                    Last calculated
                  </div>
                  <div className="font-mono text-[11px] text-text-muted">
                    {new Date(balance.last_calculated_at).toLocaleString()}
                  </div>
                </div>
              </>
            )}
          </div>
        </>
      )}
    </>
  )
}

export default function BalanceBar({ balances, onEdit, onRecalculate }: Props) {
  if (balances.length === 0) return null

  return (
    <>
      {/* Desktop table (≥lg / 1024px) */}
      <div className="hidden lg:block border border-border rounded-sm overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-background h-8 border-b border-border">
              <th className="px-3 py-1 text-left font-medium text-[10px] text-text-muted uppercase tracking-wider">Currency</th>
              <th className="px-3 py-1 text-right font-medium text-[10px] text-text-muted uppercase tracking-wider">Opening</th>
              <th className="px-3 py-1 text-right font-medium text-[10px] text-text-muted uppercase tracking-wider">Income</th>
              <th className="px-3 py-1 text-right font-medium text-[10px] text-text-muted uppercase tracking-wider">Expenses</th>
              <th className="px-3 py-1 text-right font-medium text-[10px] text-text-muted uppercase tracking-wider hidden lg:table-cell">Exch. In</th>
              <th className="px-3 py-1 text-right font-medium text-[10px] text-text-muted uppercase tracking-wider hidden lg:table-cell">Exch. Out</th>
              <th className="px-3 py-1 text-right font-medium text-[10px] text-text-muted uppercase tracking-wider border-l border-border">Closing</th>
              <th className="sr-only">Actions</th>
            </tr>
          </thead>
          <tbody>
            {balances.map((balance, index) => {
              const opening = Number(balance.opening_balance) || 0
              const income = Number(balance.total_income) || 0
              const expenses = Number(balance.total_expenses) || 0
              const exchIn = Number(balance.exchanges_in) || 0
              const exchOut = Number(balance.exchanges_out) || 0
              const closing = Number(balance.closing_balance) || 0
              const isLast = index === balances.length - 1

              return (
                <tr
                  key={balance.id}
                  className={`bg-surface hover:bg-surface-hover transition-colors h-8 border-b border-border ${isLast ? 'border-b-0' : ''}`}
                >
                  <td className="px-3 py-1 font-mono text-xs font-medium text-text text-left">
                    {balance.currency}
                  </td>
                  <td className={`px-3 py-1 font-mono text-xs font-medium text-right tabular-nums ${opening === 0 ? 'text-text-muted' : 'text-text'}`}>
                    {formatAmount(opening)}
                  </td>
                  <td className={`px-3 py-1 font-mono text-xs font-medium text-right tabular-nums ${income === 0 ? 'text-text-muted' : 'text-positive'}`}>
                    +{formatAmount(income)}
                  </td>
                  <td className={`px-3 py-1 font-mono text-xs font-medium text-right tabular-nums ${expenses === 0 ? 'text-text-muted' : 'text-negative'}`}>
                    -{formatAmount(expenses)}
                  </td>
                  <td className={`px-3 py-1 font-mono text-xs font-medium text-right tabular-nums ${exchIn === 0 ? 'text-text-muted' : 'text-text'}`}>
                    {exchIn === 0 ? formatAmount(0) : `+${formatAmount(exchIn)}`}
                  </td>
                  <td className={`px-3 py-1 font-mono text-xs font-medium text-right tabular-nums ${exchOut === 0 ? 'text-text-muted' : 'text-text'}`}>
                    {exchOut === 0 ? formatAmount(0) : `-${formatAmount(exchOut)}`}
                  </td>
                  <td className={`px-3 py-1 font-mono text-sm font-medium text-right tabular-nums border-l border-border ${closingColorClass(closing)}`}>
                    {formatAmount(closing)}
                  </td>
                  <td className="px-3 py-1">
                    <div className="relative flex justify-end">
                      <ActionsMenu balance={balance} onEdit={onEdit} onRecalculate={onRecalculate} />
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile stacked cards (<lg / 1024px) */}
      <div className="lg:hidden space-y-3">
        {balances.map((balance) => {
          const opening = Number(balance.opening_balance) || 0
          const income = Number(balance.total_income) || 0
          const expenses = Number(balance.total_expenses) || 0
          const exchIn = Number(balance.exchanges_in) || 0
          const exchOut = Number(balance.exchanges_out) || 0
          const closing = Number(balance.closing_balance) || 0
          const netExch = exchIn - exchOut
          const exch = exchangeDisplay(netExch)

          return (
            <div key={balance.id} className="bg-surface border border-border rounded-sm p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="font-mono text-xs font-medium text-text">{balance.currency}</span>
                <div className="flex items-center gap-2">
                  <span className={`font-mono text-sm font-medium tabular-nums ${closingColorClass(closing)}`}>
                    {formatAmount(closing)}
                  </span>
                  <div className="relative flex justify-end">
                    <ActionsMenu balance={balance} onEdit={onEdit} onRecalculate={onRecalculate} />
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted mb-0.5">Opening</div>
                  <div className={`font-mono text-xs font-medium tabular-nums ${opening === 0 ? 'text-text-muted' : 'text-text'}`}>
                    {formatAmount(opening)}
                  </div>
                </div>
                <div>
                  <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted mb-0.5">Income</div>
                  <div className={`font-mono text-xs font-medium tabular-nums ${income === 0 ? 'text-text-muted' : 'text-positive'}`}>
                    +{formatAmount(income)}
                  </div>
                </div>
                <div>
                  <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted mb-0.5">Expenses</div>
                  <div className={`font-mono text-xs font-medium tabular-nums ${expenses === 0 ? 'text-text-muted' : 'text-negative'}`}>
                    -{formatAmount(expenses)}
                  </div>
                </div>
                <div>
                  <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted mb-0.5">Exch. In</div>
                  <div className={`font-mono text-xs font-medium tabular-nums ${exchIn === 0 ? 'text-text-muted' : 'text-text'}`}>
                    {exchIn === 0 ? formatAmount(0) : `+${formatAmount(exchIn)}`}
                  </div>
                </div>
                <div>
                  <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted mb-0.5">Exch. Out</div>
                  <div className={`font-mono text-xs font-medium tabular-nums ${exchOut === 0 ? 'text-text-muted' : 'text-text'}`}>
                    {exchOut === 0 ? formatAmount(0) : `-${formatAmount(exchOut)}`}
                  </div>
                </div>
                <div>
                  <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted mb-0.5">Net Exch.</div>
                  <div className={`font-mono text-xs font-medium tabular-nums ${exch.color}`}>
                    {exch.text}
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </>
  )
}
