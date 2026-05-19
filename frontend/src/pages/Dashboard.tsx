import {useNavigate} from 'react-router-dom'
import {useBudgetPeriod} from '../contexts/BudgetPeriodContext'
import Loading from '../components/common/Loading'
import EmptyState from '../components/common/EmptyState'
import BalanceSection from '../components/balance/BalanceSection'

export default function Dashboard() {
    const navigate = useNavigate()

    const {selectedPeriod: period, isLoading} = useBudgetPeriod()

    if (isLoading) return <Loading/>

    if (!period) {
        return (
            <EmptyState
                message="No active budget period found for today's date."
                action={{label: "View All Periods", onClick: () => navigate('/budget-periods')}}
            />
        )
    }

    return (
        <div className="max-w-screen-2xl mx-auto">
            <BalanceSection periodId={period.id}/>
        </div>
    )
}
