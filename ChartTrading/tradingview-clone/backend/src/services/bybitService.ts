import { spawn } from 'child_process';
import path from 'path';

// Define Kline interface locally
interface Kline {
  openTime: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export class BybitService {
  private pythonScriptPath: string;

  constructor() {
    // Path to the Python trading_functions.py in the container
    // The file is copied to the root of the working directory (/app)
    this.pythonScriptPath = path.resolve(process.cwd(), 'trading_functions.py');
  }

  async getKlineData(
    category: string = 'linear',
    symbol: string = 'BTCUSDT',
    interval: string = 'D',
    limit: number = 100
  ): Promise<Kline[]> {
    return new Promise((resolve, reject) => {
      // Python script to call the get_kline_data function
      const pythonCode = `
import sys
import os
import json

# Add current directory to Python path (trading_functions.py is in the same directory)
sys.path.append('.')

try:
    from trading_functions import get_kline_data
    
    # Get kline data from Bybit
    kline_data = get_kline_data("${category}", "${symbol}", "${interval}", ${limit})
    
    # Convert to the format expected by the frontend
    formatted_data = []
    for item in kline_data:
        formatted_data.append({
            "openTime": int(item[0]),
            "open": float(item[1]),
            "high": float(item[2]),
            "low": float(item[3]),
            "close": float(item[4]),
            "volume": float(item[5])
        })
    
    # Reverse the order to have newest first (ascending time order)
    formatted_data.reverse()
    
    print(json.dumps(formatted_data))
    
except Exception as e:
    import traceback
    print(json.dumps({"error": str(e), "traceback": traceback.format_exc()}))
`;

      const pythonProcess = spawn('python3', ['-c', pythonCode], {
        stdio: ['pipe', 'pipe', 'pipe']
      });

      let output = '';
      let errorOutput = '';

      pythonProcess.stdout.on('data', (data: Buffer) => {
        output += data.toString();
      });

      pythonProcess.stderr.on('data', (data: Buffer) => {
        errorOutput += data.toString();
      });

      pythonProcess.on('close', (code: number | null) => {
        if (code !== 0) {
          console.error('Python script error:', errorOutput);
          reject(new Error(`Python script failed with code ${code}: ${errorOutput}`));
          return;
        }

        try {
          const result = JSON.parse(output.trim());
          
          if (result.error) {
            console.error('Python function error:', result.error);
            console.error('Python traceback:', result.traceback);
            reject(new Error(result.error));
            return;
          }

          resolve(result as Kline[]);
        } catch (parseError) {
          console.error('Failed to parse Python output:', output);
          reject(new Error(`Failed to parse Python output: ${parseError}`));
        }
      });

      pythonProcess.on('error', (error: Error) => {
        reject(new Error(`Failed to start Python process: ${error.message}`));
      });
    });
  }

  async getSymbols(): Promise<string[]> {
    // Return common trading pairs for now
    return [
      'BTCUSDT',
      'ETHUSDT',
      'ADAUSDT',
      'BNBUSDT',
      'XRPUSDT',
      'SOLUSDT',
      'DOTUSDT',
      'AVAXUSDT',
      'LINKUSDT',
      'LTCUSDT'
    ];
  }
}

export const bybitService = new BybitService();
