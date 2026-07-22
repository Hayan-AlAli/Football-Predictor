interface LoaderProps {
  message?: string;
}

export default function Loader({ message = 'Loading...' }: LoaderProps) {
    return (
        <div className="loading-container">
            <div className="spinner"></div>
            <span className="loading-text">{message}</span>
        </div>
    );
}
