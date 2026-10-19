import { NavLink, Route, Routes } from 'react-router-dom'
import { Dashboard } from './pages/Dashboard'
import { History } from './pages/History'
import { Monitors } from './pages/Monitors'
import styles from './App.module.css'

export default function App() {
  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}><span>CP</span><div><strong>CloudPulse</strong><small>API OBSERVABILITY</small></div></div>
        <nav aria-label="主要導覽">
          <NavLink to="/" end>總覽</NavLink>
          <NavLink to="/monitors">監測設定</NavLink>
          <NavLink to="/history">檢查歷史</NavLink>
        </nav>
        <footer><span className={styles.online} />CloudPulse v1.1<br /><small>REAL + MOCK monitoring</small></footer>
      </aside>
      <main className={styles.content}><Routes><Route path="/" element={<Dashboard />} /><Route path="/monitors" element={<Monitors />} /><Route path="/history" element={<History />} /></Routes></main>
    </div>
  )
}

