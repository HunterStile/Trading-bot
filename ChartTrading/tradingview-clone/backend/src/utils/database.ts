import { Pool } from 'pg';
import { config } from '../config/database';

const pool = new Pool(config);

export const query = (text: string, params?: any[]) => {
    return pool.query(text, params);
};

export const getClient = async () => {
    const client = await pool.connect();
    return client;
};

export const closeConnection = async () => {
    await pool.end();
};