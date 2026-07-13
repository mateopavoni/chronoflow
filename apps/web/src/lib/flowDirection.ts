import { createContext, useContext } from 'react'

export type FlowDirection = 'vertical' | 'horizontal'

const FlowDirectionContext = createContext<FlowDirection>('horizontal')

export const FlowDirectionProvider = FlowDirectionContext.Provider

export function useFlowDirection(): FlowDirection {
  return useContext(FlowDirectionContext)
}
