import React, { useState } from 'react';
import { Box, Spinner } from '@instabase.com/pollen';
import { GenericError } from '@instabase.com/pollen/illustration';
import styled from 'styled-components';

const Container = styled(Box)`
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 400px;
  margin-top: 12px;
`;

const GifImage = styled.img`
  max-width: 100%;
  height: 100%;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  object-fit: cover;
`;

interface RunGifProps {
  gifUrl?: string;
}

export const RunGif: React.FC<RunGifProps> = ({ 
  gifUrl,
}) => {
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  const handleImageLoad = () => {
    setIsLoading(false);
    setHasError(false);
  };

  const handleImageError = () => {
    setIsLoading(false);
    setHasError(true);
  };

  if (!gifUrl) {
    return null;
  }

  if (hasError) {
    return (
      <Container>
        <GenericError />
      </Container>
    );
  }

  return (
    <Container>
      {isLoading && (
        <Spinner size={32} />
      )}
      <GifImage
        src={gifUrl}
        onLoad={handleImageLoad}
        onError={handleImageError}
        style={{ display: isLoading ? 'none' : 'block' }}
        alt="GIF animation"
      />
    </Container>
  );
};
