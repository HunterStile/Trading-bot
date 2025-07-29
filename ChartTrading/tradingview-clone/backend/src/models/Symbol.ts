import mongoose, { Schema, Document } from 'mongoose';

export interface ISymbol extends Document {
    name: string;
    ticker: string;
    exchange: string;
    currency: string;
    sector?: string;
    industry?: string;
    description?: string;
    isActive: boolean;
    createdAt: Date;
    updatedAt: Date;
}

const SymbolSchema: Schema = new Schema({
    name: { type: String, required: true },
    ticker: { type: String, required: true, unique: true },
    exchange: { type: String, required: true },
    currency: { type: String, required: true },
    sector: { type: String },
    industry: { type: String },
    description: { type: String },
    isActive: { type: Boolean, default: true }
}, {
    timestamps: true
});

export const Symbol = mongoose.model<ISymbol>('Symbol', SymbolSchema);