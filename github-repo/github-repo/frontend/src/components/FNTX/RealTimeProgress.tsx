import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useTradeUpdates, WebSocketMessage } from '@/hooks/useWebSocket';
import { 
  Brain, 
  Zap, 
  TrendingUp, 
  Monitor, 
  Database,
  Loader2,
  CheckCircle,
  XCircle,
  AlertCircle
} from 'lucide-react';

interface RealTimeProgressProps {
  tradeId: string | null;
  isActive: boolean;
}

interface ProgressStep {
  id: string;
  message: string;
  timestamp: string;
  progress?: number;
  status: 'pending' | 'active' | 'completed' | 'failed';
}

export const RealTimeProgress: React.FC<RealTimeProgressProps> = ({ 
  tradeId, 
  isActive 
}) => {
  const { isConnected, messages, lastMessage } = useTradeUpdates(tradeId);
  const [currentProgress, setCurrentProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState<string>('');
  const [steps, setSteps] = useState<ProgressStep[]>([]);
  const [status, setStatus] = useState<'idle' | 'running' | 'completed' | 'failed'>('idle');

  useEffect(() => {
    if (lastMessage) {
      handleWebSocketMessage(lastMessage);
    }
  }, [lastMessage]);

  const handleWebSocketMessage = (message: WebSocketMessage) => {
    switch (message.type) {
      case 'connection_established':
        setStatus('idle');
        setSteps([]);
        setCurrentProgress(0);
        break;

      case 'orchestration_start':
        setStatus('running');
        setCurrentStep(message.message || 'Starting...');
        setSteps([{
          id: 'start',
          message: message.message || 'Starting orchestration...',
          timestamp: message.timestamp,
          status: 'completed'
        }]);
        break;

      case 'computation_step':
        setCurrentStep(message.message || '');
        setCurrentProgress(message.progress ? message.progress * 100 : 0);
        
        setSteps(prev => {
          const newStep: ProgressStep = {
            id: message.step || `step_${prev.length}`,
            message: message.message || '',
            timestamp: message.timestamp,
            progress: message.progress,
            status: 'active'
          };
          
          // Mark previous steps as completed
          const updatedSteps = prev.map(step => ({ ...step, status: 'completed' as const }));
          return [...updatedSteps, newStep];
        });
        break;

      case 'orchestration_complete':
        setStatus('completed');
        setCurrentProgress(100);
        setCurrentStep('✅ Orchestration completed successfully!');
        
        setSteps(prev => prev.map(step => ({ ...step, status: 'completed' as const })));
        break;

      case 'orchestration_failed':
      case 'orchestration_error':
        setStatus('failed');
        setCurrentStep(`❌ ${message.message || 'Orchestration failed'}`);
        
        setSteps(prev => {
          const lastStep = prev[prev.length - 1];
          if (lastStep) {
            lastStep.status = 'failed';
          }
          return [...prev];
        });
        break;
    }
  };

  const getStepIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'active':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusBadge = () => {
    switch (status) {
      case 'running':
        return <Badge className="bg-blue-500">🔄 Running</Badge>;
      case 'completed':
        return <Badge className="bg-green-500">✅ Completed</Badge>;
      case 'failed':
        return <Badge variant="destructive">❌ Failed</Badge>;
      default:
        return <Badge variant="outline">⏸️ Idle</Badge>;
    }
  };

  if (!isActive || !tradeId) {
    return (
      <Card className="opacity-50">
        <CardHeader>
          <CardTitle className="text-sm">FNTX's Computer - Real-time Progress</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-muted-foreground py-8">
            No active orchestration
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">FNTX's Computer - Real-time Progress</CardTitle>
          <div className="flex items-center gap-2">
            {getStatusBadge()}
            <Badge variant="outline">
              {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Current Progress */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span>Overall Progress</span>
            <span className="font-mono">{Math.round(currentProgress)}%</span>
          </div>
          <Progress value={currentProgress} className="h-2" />
          
          {currentStep && (
            <div className="text-xs text-muted-foreground mt-2">
              {currentStep}
            </div>
          )}
        </div>

        {/* Step Details */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium">Agent Activity</h4>
          <ScrollArea className="h-48 w-full">
            <div className="space-y-2">
              {steps.length === 0 ? (
                <div className="text-muted-foreground text-xs italic">
                  Waiting for agent activity...
                </div>
              ) : (
                steps.map((step, index) => (
                  <div key={step.id} className="flex items-start gap-2 text-xs">
                    <div className="mt-0.5">
                      {getStepIcon(step.status)}
                    </div>
                    <div className="flex-1 space-y-1">
                      <div className="font-mono">{step.message}</div>
                      <div className="text-muted-foreground">
                        {new Date(step.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        </div>

        {/* Trade ID */}
        <div className="text-xs text-muted-foreground border-t pt-2">
          Trade ID: <span className="font-mono">{tradeId}</span>
        </div>
      </CardContent>
    </Card>
  );
};