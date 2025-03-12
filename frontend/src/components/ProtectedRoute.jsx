import {Navigate, Route} from 'react-router-dom';
import {jwtDecode} from '../utils/jwtDecode';
import api from '../api';
import {ACCESS_TOKEN, REFRESH_TOKEN} from '../constants';
import {useState, useEffect} from 'react';

function ProtectedRoute({childen}){
    const [isAuthorized, setIsAuthorized] = useState(null);

    useEffect(() => {
        auth().catch(() => setIsAuthorized(false)); 
    }, []);

    const refreshToken = async () => {
        const refreshToken = localStorage.getItem(REFRESH_TOKEN);
        try{
            const res = await api.post('/api/token/refresh/', {
                refreshToken,
            });
            if(res.status === 200){
                localStorage.setItem(ACCESS_TOKEN, res.data.access);
                setIsAuthorized(true);
            } else {
                setIsAuthorized(false);
            }
        }catch(error){
            console.error(error);
            setIsAuthorized(false);
        }
    }
    const auth = async () => {
        const token = localStorage.getItem(ACCESS_TOKEN);
        if(!token){
            setIsAuthorized(false);
            return;
        }
        const decoded = jwtDecode(token);
        if(decoded.exp * 1000 < Date.now()){
            await refreshToken();
        } else { 
            api.get('/auth')
                .then(() => setIsAuthorized(true))
                .catch(() => setIsAuthorized(false));
        }
    }

    if(isAuthorized === null){
        return <div>Loading ...</div>;
    }

    return isAuthorized ? children : <Navigate to="/login" />;
}

export default ProtectedRoute;