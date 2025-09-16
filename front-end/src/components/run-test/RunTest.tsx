import React, { useState } from 'react';
import { Input, Modal } from '@instabase.com/pollen';

export interface RunTestFormData {
  runName: string;
  testUrl: string;
  userName: string;
  password: string;
}

export interface RunTestProps {
  isOpen: boolean;
  onClose: () => void;
  onRunTest: (formData: RunTestFormData) => void;
  testName: string;
}

export const RunTest: React.FC<RunTestProps> = ({
  isOpen,
  onClose,
  onRunTest,
  testName = ''
}) => {
  const [formData, setFormData] = useState<RunTestFormData>({
    runName: '',
    testUrl: '',
    userName: '',
    password: ''
  });

  const handleInputChange = (field: keyof RunTestFormData, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleRunTest = () => {
    onRunTest(formData);
    onClose();
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
        />
      </Modal.Body>

      <Modal.Footer
        fullWidth={true}
        onCancel={handleCancel}
        onConfirm={handleRunTest}
        confirmButtonProps={{
          label: 'Run test',
          intent: 'primary',
          disabled: !formData.runName || !formData.testUrl || !formData.userName || !formData.password,
        }}
        cancelButtonProps={{
          label: 'Cancel',
          intent: 'secondary',
        }}
      />
    </Modal>
  );
};
