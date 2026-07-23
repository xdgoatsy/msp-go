import React from 'react';
import { Bot, Boxes, Cloud, Gem, Sparkles } from 'lucide-react';
import { cn } from '@/libs/utils/cn';

interface ChannelProviderIconProps {
  code: string;
  className?: string;
}

export const ChannelProviderIcon: React.FC<ChannelProviderIconProps> = ({ code, className }) => {
  const iconClassName = cn('h-5 w-5', className);
  switch (code) {
    case 'openai':
    case 'openai-responses':
      return <Sparkles className={iconClassName} aria-hidden="true" />;
    case 'gemini':
      return <Gem className={iconClassName} aria-hidden="true" />;
    case 'anthropic':
      return <Boxes className={iconClassName} aria-hidden="true" />;
    case 'custom':
      return <Cloud className={iconClassName} aria-hidden="true" />;
    default:
      return <Bot className={iconClassName} aria-hidden="true" />;
  }
};
