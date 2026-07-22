interface HeaderProps {
  matchCount?: number;
}

export default function Header({ matchCount = 0 }: HeaderProps) {
    return (
        <header className="header">
            <div className="container header-content">
                <div className="logo">
                    <div className="logo-icon">FP</div>
                    <span className="logo-text">Football Predictor</span>
                </div>

                <div className="header-stats">
                    <div className="stat-item">
                        <div className="stat-value">{matchCount}</div>
                        <div className="stat-label">Matches</div>
                    </div>
                </div>
            </div>
        </header>
    );
}
