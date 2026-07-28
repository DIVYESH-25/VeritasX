import React, { createContext, useContext, useState, ReactNode } from 'react';

export type CursorType = 'default' | 'button' | 'card' | 'image' | 'scan' | 'text';

interface CursorContextProps {
  cursorType: CursorType;
  cursorLabel: string;
  setCursor: (type: CursorType, label?: string) => void;
  resetCursor: () => void;
}

const CursorContext = createContext<CursorContextProps>({
  cursorType: 'default',
  cursorLabel: '',
  setCursor: () => {},
  resetCursor: () => {},
});

export const CursorProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [cursorType, setCursorType] = useState<CursorType>('default');
  const [cursorLabel, setCursorLabel] = useState<string>('');

  const setCursor = (type: CursorType, label: string = '') => {
    setCursorType(type);
    setCursorLabel(label);
  };

  const resetCursor = () => {
    setCursorType('default');
    setCursorLabel('');
  };

  return (
    <CursorContext.Provider value={{ cursorType, cursorLabel, setCursor, resetCursor }}>
      {children}
    </CursorContext.Provider>
  );
};

export const useCursorState = () => useContext(CursorContext);
