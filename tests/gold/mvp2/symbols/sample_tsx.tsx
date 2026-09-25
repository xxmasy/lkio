// Gold Fixture: TSX React Component and Hook
import React, { useState } from 'react';

export interface CardProps {
    title: string;
    count: number;
}

export function useCardCounter(initial: number) {
    const [count, setCount] = useState(initial);
    return { count, setCount };
}

export const StatsCard = (props: CardProps) => {
    const { count } = useCardCounter(props.count);
    return (
        <div className="card">
            <h3>{props.title}</h3>
            <span>{count}</span>
        </div>
    );
};
