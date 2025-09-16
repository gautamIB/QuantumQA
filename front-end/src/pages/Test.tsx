import React from 'react';
import { TESTS } from '../data';
import { useMatch } from 'react-router-dom';
import { ViewTest } from './ViewTest';

export const Test: React.FC = () => {
    const match = useMatch('/tests/:id');
    if (match) {
        const testId = match.params.id;
        const test = TESTS.find(test => test.id === testId);
        if (test) {
            return (
                <ViewTest test={test} />
            );
        }
    }
    return null;
};

