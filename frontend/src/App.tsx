import { NavLink, Route, Routes } from 'react-router-dom'
import { Dashboard } from './pages/Dashboard'
import { History } from './pages/History'
import { Monitors } from './pages/Monitors'
import styles from './App.module.css'

export default function App() {
  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <span className={styles.brandMark} aria-hidden="true">
            <svg viewBox="0 0 32 32"><path d="M5 17h5l2.5-7 4.5 14 3.5-11 2 4H27" /></svg>
          </span>
          <div><strong>CloudPulse</strong><small>API 健康監測</small></div>
        </div>
        <nav aria-label="主要導覽">
          <NavLink to="/" end>總覽</NavLink>
          <NavLink to="/monitors">監測設定</NavLink>
          <NavLink to="/history">檢查歷史</NavLink>
        </nav>
        <footer><span className={styles.online} />系統連線中<br /><small>CloudPulse v1.1</small></footer>
      </aside>
      <header className={styles.topbar}>
        <div><span className={styles.online} />Production workspace <span className={styles.separator}>/</span> asia-east1</div>
        <span>頁面每 60 秒更新</span>
      </header>
      <main className={styles.content}><Routes><Route path="/" element={<Dashboard />} /><Route path="/monitors" element={<Monitors />} /><Route path="/history" element={<History />} /></Routes></main>
    </div>
  )
}

