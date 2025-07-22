import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { useFNTXComputer } from '@/hooks/useWebSocket';
import { 
  Activity, 
  Brain, 
  Cpu, 
  Database, 
  TrendingUp, 
  Zap,
  Monitor,
  Wifi,
  WifiOff
} from 'lucide-react';

interface SystemMetrics {
  cpu_usage: string;
  memory_usage: string;
  active_trades: number;
  market_data: string;
  neural_network: string;
}

interface AgentStatus {
  strategic_planner: string;
  executor: string;
  evaluator: string;
  environment_watcher: string;
  reward_model: string;
}

export const FNTXComputer: React.FC = () => {
  const { isConnected, messages, lastMessage, error } = useFNTXComputer();
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics>({
    cpu_usage: '0%',
    memory_usage: '0MB',
    active_trades: 0,
    market_data: 'offline',
    neural_network: 'standby'
  });
  const [agentStatus, setAgentStatus] = useState<AgentStatus>({
    strategic_planner: 'standby',
    executor: 'standby',
    evaluator: 'standby',
    environment_watcher: 'standby',
    reward_model: 'standby'
  });
  const [computationLogs, setComputationLogs] = useState<string[]>([]);

  useEffect(() => {
    if (lastMessage) {
      switch (lastMessage.type) {
        case 'fntx_computer_init':
          setAgentStatus(lastMessage.data?.agents_status || agentStatus);
          setComputationLogs(prev => [...prev, `🖥️ FNTX's Computer Online - ${new Date().toLocaleTimeString()}`]);
          break;
        case 'system_metrics':
          setSystemMetrics({
            cpu_usage: lastMessage.data?.cpu_usage || '0%',
            memory_usage: lastMessage.data?.memory_usage || '0MB',
            active_trades: lastMessage.data?.active_trades || 0,
            market_data: lastMessage.data?.market_data || 'offline',
            neural_network: lastMessage.data?.neural_network || 'standby'
          });
          break;
        case 'computation_step':
        case 'orchestration_start':
        case 'orchestration_complete':
        case 'orchestration_failed':
          if (lastMessage.message) {
            setComputationLogs(prev => [...prev, `${lastMessage.message} - ${new Date().toLocaleTimeString()}`]);
          }
          break;
      }
    }
  }, [lastMessage]);

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
      case 'running':
      case 'monitoring':
      case 'learning':
      case 'streaming':
        return 'bg-green-500';
      case 'standby':
      case 'ready':
        return 'bg-yellow-500';
      case 'offline':
      case 'failed':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getAgentIcon = (agentName: string) => {
    switch (agentName) {
      case 'strategic_planner':
        return <Brain className="h-4 w-4" />;
      case 'executor':
        return <Zap className="h-4 w-4" />;
      case 'evaluator':
        return <TrendingUp className="h-4 w-4" />;
      case 'environment_watcher':
        return <Monitor className="h-4 w-4" />;
      case 'reward_model':
        return <Database className="h-4 w-4" />;
      default:
        return <Activity className="h-4 w-4" />;
    }
  };

  const formatAgentName = (name: string) => {
    return name.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2">
            <Cpu className="h-5 w-5" />
            FNTX's Computer
            <div className="flex items-center gap-2 ml-auto">
              {isConnected ? (
                <Badge variant="default" className="bg-green-500">
                  <Wifi className="h-3 w-3 mr-1" />
                  Connected
                </Badge>
              ) : (
                <Badge variant="destructive">
                  <WifiOff className="h-3 w-3 mr-1" />
                  Disconnected
                </Badge>
              )}
            </div>
          </CardTitle>
        </CardHeader>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* System Metrics */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">System Metrics</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>CPU Usage</span>
                <span className="font-mono">{systemMetrics.cpu_usage}</span>
              </div>
              <Progress value={parseInt(systemMetrics.cpu_usage)} className="h-2" />
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Memory</span>
                <span className="font-mono">{systemMetrics.memory_usage}</span>
              </div>
              <Progress value={65} className="h-2" />
            </div>

            <Separator />
            
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Active Trades</span>
                <div className="font-mono text-lg">{systemMetrics.active_trades}</div>
              </div>
              <div>
                <span className="text-muted-foreground">Neural Network</span>
                <div className="flex items-center gap-1">
                  <div className={`w-2 h-2 rounded-full ${getStatusColor(systemMetrics.neural_network)}`} />
                  <span className="capitalize">{systemMetrics.neural_network}</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Agent Status */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">AI Agent Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {Object.entries(agentStatus).map(([agent, status]) => (
              <div key={agent} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {getAgentIcon(agent)}
                  <span className="text-sm">{formatAgentName(agent)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${getStatusColor(status)}`} />
                  <span className="text-xs capitalize text-muted-foreground">
                    {status}
                  </span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Computation Logs */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Real-time Computations</CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-64 w-full">
            <div className="space-y-1">
              {computationLogs.length === 0 ? (
                <div className="text-muted-foreground text-sm italic">
                  Waiting for computations...
                </div>
              ) : (
                computationLogs.slice(-20).reverse().map((log, index) => (
                  <div key={index} className="text-xs font-mono bg-muted/50 p-2 rounded">
                    {log}
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Error Display */}
      {error && (
        <Card className="border-red-200">
          <CardContent className="pt-6">
            <div className="text-red-600 text-sm">
              ⚠️ Connection Error: {error}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};