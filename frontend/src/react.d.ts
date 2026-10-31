/**
 * Ambient type declarations for React and JSX
 * Allows VS Code TypeScript engine to validate JSX without local node_modules
 */

declare namespace React {
  export function useState<T>(initialState: T | (() => T)): [T, (value: T | ((prevState: T) => T)) => void];
  export function useEffect(effect: () => void | (() => void), deps?: any[]): void;
  export function useCallback<T extends (...args: any[]) => any>(callback: T, deps: any[]): T;
  export function useMemo<T>(factory: () => T, deps: any[]): T;
  export function useRef<T>(initialValue?: T): { current: T };
  export type FC<P = {}> = (props: P) => any;
  export type ReactNode = any;
  export type MouseEvent = any;
  export function createElement(type: any, props?: any, ...children: any[]): any;
}

declare module 'react' {
  export = React;
}

declare namespace JSX {
  interface Element extends React.ReactNode {}
  interface IntrinsicElements {
    [elemName: string]: any;
  }
}
