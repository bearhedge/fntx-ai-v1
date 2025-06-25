import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Brain, Activity, ChevronDown } from 'lucide-react';
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useFNTXComputer } from '@/hooks/useWebSocket';
import { toast } from 'sonner';

interface ComputationStep {
  timestamp: string;
  message: string;
  indent?: number;
}

export const FNTXComputer: React.FC = () => {
  const { isConnected, messages, lastMessage, error } = useFNTXComputer();
  const [computationSteps, setComputationSteps] = useState<ComputationStep[]>([]);
  const [currentTime, setCurrentTime] = useState<string>('');
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(new Date().toLocaleTimeString('en-US', { 
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      }));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const runFeatureEngineering = async () => {
    try {
      setIsRunning(true);
      setComputationSteps([]); // Clear previous steps
      
      const response = await fetch('/api/ml/feature-engineering', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const result = await response.json();
        toast.success('Feature engineering pipeline started!');
      } else {
        toast.error('Failed to start feature engineering');
      }
    } catch (error) {
      console.error('Error starting feature engineering:', error);
      toast.error('Error connecting to server');
    } finally {
      setIsRunning(false);
    }
  };

  const runModelTraining = async () => {
    try {
      setIsRunning(true);
      setComputationSteps([]); // Clear previous steps
      
      const response = await fetch('/api/ml/train-models', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const result = await response.json();
        toast.success('Model training pipeline started!');
      } else {
        toast.error('Failed to start model training');
      }
    } catch (error) {
      console.error('Error starting model training:', error);
      toast.error('Error connecting to server');
    } finally {
      setIsRunning(false);
    }
  };

  useEffect(() => {
    if (lastMessage) {
      // Process SPY-specific trading messages
      switch (lastMessage.type) {
        case 'fntx_computer_init':
          addStep('System initialized. Ready for SPY options analysis.');
          break;
          
        case 'market_analysis':
          addStep('> Market Analysis');
          if (lastMessage.data?.spy_price) {
            addStep(`Current State: ${lastMessage.data.market_state || 'Analyzing...'}`, 1);
            addStep(`SPY: $${lastMessage.data.spy_price}`, 1);
            addStep(`Morning Range: $${lastMessage.data.morning_range || '0.00'}`, 1);
            addStep(`Volatility Regime: ${lastMessage.data.volatility || 'Normal'}`, 1);
          }
          break;
          
        case 'position_sizing':
          addStep('> Position Sizing Calculation');
          if (lastMessage.data) {
            addStep(`Account Size: HK$${lastMessage.data.account_size || '80,000'}`, 1);
            addStep(`Daily Risk Budget: HK$${lastMessage.data.daily_risk || '2,400'}`, 1);
            addStep(`Current Risk Used: HK$${lastMessage.data.risk_used || '0'}`, 1);
            addStep(`Recommended Size: ${lastMessage.data.contracts || '1'} contract`, 1);
          }
          break;
          
        case 'strike_selection':
          addStep('> Strike Selection Process');
          if (lastMessage.data) {
            addStep(`Scanning: ${lastMessage.data.range || 'Calculating...'}`, 1);
            addStep(`Volume Analysis: ${lastMessage.data.volume_status || 'In progress...'}`, 1);
            if (lastMessage.data.selected_strike) {
              addStep(`Selected: ${lastMessage.data.selected_strike}`, 1);
            }
          }
          break;
          
        case 'risk_assessment':
          addStep('> Risk Assessment');
          if (lastMessage.data) {
            addStep(`Strike: ${lastMessage.data.strike || 'TBD'}`, 1);
            addStep(`Distance from Spot: ${lastMessage.data.otm_distance || '0'}% OTM`, 1);
            addStep(`Historical Touch Rate: ${lastMessage.data.touch_rate || '0'}%`, 1);
            addStep(`Stop Loss: $${lastMessage.data.stop_loss || '0.00'}`, 1);
            addStep(`Max Loss: HK$${lastMessage.data.max_loss || '0'}`, 1);
          }
          break;
          
        case 'computation_step':
        case 'orchestration_start':
        case 'orchestration_complete':
        case 'orchestration_failed':
          if (lastMessage.message) {
            addStep(lastMessage.message);
          }
          break;
      }
    }
  }, [lastMessage]);

  const addStep = (message: string, indent: number = 0) => {
    const step: ComputationStep = {
      timestamp: new Date().toLocaleTimeString('en-US', { 
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      }),
      message,
      indent
    };
    setComputationSteps(prev => [...prev.slice(-50), step]); // Keep last 50 steps
  };

  return (
    <Card className="h-full">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-normal">FNTX Computer</CardTitle>
          <div className="flex items-center gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={isRunning || !isConnected}
                  className="text-xs"
                >
                  {isRunning ? (
                    <>
                      <Activity className="h-3 w-3 mr-1 animate-pulse" />
                      Running...
                    </>
                  ) : (
                    <>
                      <Brain className="h-3 w-3 mr-1" />
                      Run Computations
                      <ChevronDown className="h-3 w-3 ml-1" />
                    </>
                  )}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={runFeatureEngineering}>
                  <Brain className="h-3 w-3 mr-2" />
                  Feature Engineering
                </DropdownMenuItem>
                <DropdownMenuItem onClick={runModelTraining}>
                  <Activity className="h-3 w-3 mr-2" />
                  Model Training
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            <span className="text-xs text-muted-foreground font-mono">
              {currentTime}
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="h-[500px] px-6">
          <div className="space-y-0.5 font-mono text-xs">
            {computationSteps.length === 0 ? (
              <div className="text-muted-foreground py-4">
                Waiting for market data...
              </div>
            ) : (
              computationSteps.map((step, index) => (
                <div 
                  key={index} 
                  className="leading-relaxed"
                  style={{ paddingLeft: `${step.indent || 0}rem` }}
                >
                  {step.message}
                </div>
              ))
            )}
            {!isConnected && (
              <div className="text-muted-foreground mt-4">
                Connection lost. Reconnecting...
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
};