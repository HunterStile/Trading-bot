export interface WebSocketMessage {
    type: string;
    payload: any;
}

export interface WebSocketResponse {
    event: string;
    data: any;
}

export interface WebSocketError {
    code: number;
    message: string;
}