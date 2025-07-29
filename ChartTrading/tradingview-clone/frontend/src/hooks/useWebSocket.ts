import { useEffect, useRef, useState } from 'react';

const useWebSocket = (url: string) => {
    const [data, setData] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);
    const [isConnected, setIsConnected] = useState<boolean>(false);
    const socketRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        socketRef.current = new WebSocket(url);

        socketRef.current.onopen = () => {
            setIsConnected(true);
        };

        socketRef.current.onmessage = (event) => {
            const parsedData = JSON.parse(event.data);
            setData(parsedData);
        };

        socketRef.current.onerror = (event) => {
            setError(`WebSocket error: ${event}`);
        };

        socketRef.current.onclose = () => {
            setIsConnected(false);
        };

        return () => {
            socketRef.current?.close();
        };
    }, [url]);

    return { data, error, isConnected };
};

export default useWebSocket;