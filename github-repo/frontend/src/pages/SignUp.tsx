import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { GoogleLoginButton } from '@/components/Auth/GoogleLoginButton';
import { useAuth } from '@/contexts/AuthContext';
import { Eye, EyeOff, Loader2, Check, X } from 'lucide-react';

const SignUp = () => {
  const navigate = useNavigate();
  
  // Get auth context safely
  let login: any;
  try {
    const auth = useAuth();
    login = auth.login;
  } catch (err) {
    console.error('Auth context error:', err);
    // Provide a fallback login function
    login = async (token: string) => {
      // Simple fallback that just stores the token
      document.cookie = `fntx_token=${token}; path=/; max-age=604800`;
    };
  }
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [passwordErrors, setPasswordErrors] = useState<string[]>([]);

  const validatePassword = (password: string) => {
    const errors: string[] = [];
    if (password.length < 8) errors.push('At least 8 characters');
    if (!/[A-Z]/.test(password)) errors.push('One uppercase letter');
    if (!/[a-z]/.test(password)) errors.push('One lowercase letter');
    if (!/\d/.test(password)) errors.push('One number');
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) errors.push('One special character');
    return errors;
  };

  const handlePasswordChange = (password: string) => {
    setFormData({ ...formData, password });
    setPasswordErrors(validatePassword(password));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validate passwords match
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    // Validate password strength
    const errors = validatePassword(formData.password);
    if (errors.length > 0) {
      setError('Please meet all password requirements');
      return;
    }

    setIsLoading(true);

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8002';
      const response = await fetch(`${apiUrl}/api/auth/signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: formData.name,
          email: formData.email,
          password: formData.password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        if (data.detail?.issues) {
          throw new Error(data.detail.issues.join(', '));
        }
        throw new Error(data.detail || 'Sign up failed');
      }

      // Use the login method from AuthContext to handle the token and user data
      await login(data.token);
      
      // Navigate to main app
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred during sign up');
    } finally {
      setIsLoading(false);
    }
  };

  const getPasswordStrength = () => {
    const errors = validatePassword(formData.password);
    if (formData.password.length === 0) return null;
    if (errors.length === 0) return 'strong';
    if (errors.length <= 2) return 'medium';
    return 'weak';
  };

  const strengthColors = {
    weak: 'bg-red-500',
    medium: 'bg-yellow-500',
    strong: 'bg-green-500',
  };

  return (
    <div className="min-h-screen bg-[#6A6A6A] flex flex-col items-center px-4 pt-20 pb-10 overflow-y-auto">
      {/* White FNTX Logo */}
      <div className="flex justify-center mb-8">
        <svg width="200" height="109" viewBox="0 0 640 346" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M206.163 114.61H282.436V140.503H257.293V252.614H230.649V140.503H206.163V114.61Z" fill="white"/>
          <path d="M85.3193 114.61H110.462L169.661 205.424V114.61H195.929V252.614H170.693L111.588 162.081V252.614H85.3193V114.61Z" fill="white"/>
          <path d="M0.970947 114.61H69.4572V140.222H26.9582V165.271H69.4572V190.507H26.9582V252.614H0.970947V114.61Z" fill="white"/>
          <path d="M233.027 140.49V114.63H315.312L356.552 167.06C356.552 167.06 441.402 54.52 639.792 -0.0100098C639.792 -0.0100098 478.182 51.02 352.362 211.8C338.382 193.63 292.942 140.5 292.942 140.5H270.371H260.287H233.027V140.49Z" fill="white"/>
          <path d="M319.852 189.43L341.872 216.34L213.252 346.01L319.852 189.43Z" fill="#AAAAAA"/>
          <path d="M362.152 215.17L403.392 262.82H446.032L384.512 185.93L362.152 215.17Z" fill="#AAAAAA"/>
        </svg>
      </div>

      {/* Sign Up Form */}
      <div className="w-full max-w-md">
        <div className="bg-[#F2F2F2] rounded-lg p-6 sm:p-8">
          <h2 className="text-2xl font-bold text-black text-center mb-6">Create account</h2>
          
          {error && (
            <Alert className="mb-4 bg-red-900/20 border-red-900">
              <AlertDescription className="text-red-400">{error}</AlertDescription>
            </Alert>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="name" className="text-black">Name</Label>
              <Input
                id="name"
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Enter your name"
                required
                className="bg-white border-gray-300 text-black placeholder-gray-400"
              />
            </div>

            <div>
              <Label htmlFor="email" className="text-black">Email</Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="Enter your email"
                required
                className="bg-white border-gray-300 text-black placeholder-gray-400"
              />
            </div>

            <div>
              <Label htmlFor="password" className="text-black">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={formData.password}
                  onChange={(e) => handlePasswordChange(e.target.value)}
                  placeholder="Create a password"
                  required
                  className="bg-white border-gray-300 text-black placeholder-gray-400 pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              
              {/* Password strength indicator */}
              {formData.password && (
                <div className="mt-2">
                  <div className="flex gap-1 mb-2">
                    {[1, 2, 3].map((level) => (
                      <div
                        key={level}
                        className={`h-1 flex-1 rounded ${
                          getPasswordStrength() === 'strong' ||
                          (getPasswordStrength() === 'medium' && level <= 2) ||
                          (getPasswordStrength() === 'weak' && level === 1)
                            ? strengthColors[getPasswordStrength()!]
                            : 'bg-gray-400'
                        }`}
                      />
                    ))}
                  </div>
                  <div className="text-xs space-y-1">
                    {['At least 8 characters', 'One uppercase letter', 'One lowercase letter', 'One number', 'One special character'].map((req) => {
                      const isMet = !passwordErrors.includes(req);
                      return (
                        <div key={req} className={`flex items-center gap-1 ${isMet ? 'text-green-600' : 'text-gray-600'}`}>
                          {isMet ? <Check size={12} /> : <X size={12} />}
                          <span>{req}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            <div>
              <Label htmlFor="confirmPassword" className="text-black">Confirm Password</Label>
              <div className="relative">
                <Input
                  id="confirmPassword"
                  type={showConfirmPassword ? 'text' : 'password'}
                  value={formData.confirmPassword}
                  onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                  placeholder="Confirm your password"
                  required
                  className="bg-white border-gray-300 text-black placeholder-gray-400 pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                >
                  {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              disabled={isLoading}
              className="w-full bg-black text-white hover:bg-gray-800"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating account...
                </>
              ) : (
                'Sign up'
              )}
            </Button>
          </form>

          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-400"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="bg-[#F2F2F2] px-4 text-gray-600">Or continue with</span>
              </div>
            </div>

            <div className="mt-6">
              <GoogleLoginButton />
            </div>
          </div>

          <p className="mt-6 text-center text-sm text-gray-700">
            Already have an account?{' '}
            <Link to="/signin" className="text-black font-semibold hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default SignUp;