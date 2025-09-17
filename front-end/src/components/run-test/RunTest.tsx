import React, { useState } from 'react';
import { Input, Modal } from '@instabase.com/pollen';
import { TEST_OPTIONS } from '../../constants';

export interface RunTestFormData {
  runName: string;
  testUrl: string;
  userName: string;
  password: string;
  apiKey: string;
}

export interface RunTestProps {
  isOpen: boolean;
  onClose: () => void;
  onRunTest: (formData: RunTestFormData) => void;
  testName: string;
  testType: string;
  isLoading: boolean;
}

export const RunTest: React.FC<RunTestProps> = ({
  isOpen,
  onClose,
  onRunTest,
  testName = '',
  testType = '',
  isLoading = false
}) => {
  const [formData, setFormData] = useState<RunTestFormData>({
    runName: '',
    testUrl: '',
    userName: '',
    password: '',
    apiKey: ''
  });

  const handleInputChange = (field: keyof RunTestFormData, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleRunTest = () => {
    onRunTest(formData);
  };

  const handleCancel = () => {
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <Modal.Header title={`Run ${testName}`} />
      <Modal.Body>
        <Input
            label="Run name"
            value={formData.runName}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => 
                handleInputChange('runName', e.target.value)
            }
            placeholder={`Run ${testName}`}
            fullWidth
            required
            mb={5}
        />

        <Input
            label="Test URL"
            value={formData.testUrl}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => 
                handleInputChange('testUrl', e.target.value)
            }
            placeholder="https://..."
            type="url"
            fullWidth
            required
            mb={5}
        />

        <Input
            label="User name"
            value={formData.userName}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => 
                handleInputChange('userName', e.target.value)
            }
            placeholder=""
            fullWidth
            required
            mb={5}
        />

        <Input
            label="Password"
            value={formData.password}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => 
                handleInputChange('password', e.target.value)
            }
            type="password"
            placeholder=""
            fullWidth
            required
            mb={5}
        />
        {testType === TEST_OPTIONS.API_TEST && (
          <Input
            label="API Key"
            value={formData.apiKey}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => 
                handleInputChange('apiKey', e.target.value)
            }
            type="password"
            placeholder=""
            fullWidth
            required
          />
        )}
      </Modal.Body>

      <Modal.Footer
        fullWidth={true}
        onCancel={handleCancel}
        onConfirm={handleRunTest}
        confirmButtonProps={{
          label: 'Run test',
          intent: 'primary',
          disabled: !formData.runName || !formData.testUrl || !formData.userName || !formData.password || isLoading,
          loading: isLoading,
        }}
        cancelButtonProps={{
          label: 'Cancel',
          intent: 'secondary',
          disabled: isLoading,
          loading: isLoading,
        }}
      />
    </Modal>
  );
};
