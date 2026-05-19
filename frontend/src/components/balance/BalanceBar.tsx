import type { PeriodBalance } from '../../types'

interface Props {
  balances: PeriodBalance[]
  onSelect: (balance: PeriodBalance) => void
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

export default function BalanceBar({ balances, onSelect }: Props) {
  if (balances.length === 0) return null

  return (
    <div className="border border-border rounded-sm overflow-hidden">
      {balances.map((balance, index) => {
        const closing = Number(balance.closing_balance) || 0
        const isLast = index === balances.length - 1

        return (
          <button
            key={balance.id}
            type="button"
            onClick={() => onSelect(balance)}
            className={`w-full flex items-center justify-between h-10 px-4 bg-surface hover:bg-surface-hover transition-colors cursor-pointer text-left ${isLast ? '' : 'border-b border-border'}`}
          >
            <span className="font-mono text-sm font-medium text-text">
              {balance.currency}
            </span>
            <span className={`font-mono text-base font-medium tabular-nums ${closingColorClass(closing)}`}>
              {formatAmount(closing)}
            </span>
          </button>
        )
      })}
    </div>
  )
}
