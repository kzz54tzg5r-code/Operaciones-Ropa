import streamlit as st

USERS = {
    'admin': {'password':'admin123', 'role':'Administrador'},
    'gerente': {'password':'gerente123', 'role':'Gerente'},
    'consulta': {'password':'consulta123', 'role':'Consulta'},
}

def login_box():
    if 'user' in st.session_state:
        return st.session_state['user']
    with st.sidebar:
        st.subheader('Acceso')
        u = st.text_input('Usuario')
        p = st.text_input('Contraseña', type='password')
        if st.button('Entrar'):
            if u in USERS and USERS[u]['password'] == p:
                st.session_state['user'] = {'name': u, 'role': USERS[u]['role']}
                st.rerun()
            else:
                st.error('Usuario o contraseña incorrectos')
    return None

def require_login():
    user = login_box()
    if not user:
        st.info('Ingresa con un usuario para continuar. Usuario demo: admin / admin123')
        st.stop()
    st.sidebar.success(f"{user['name']} · {user['role']}")
    if st.sidebar.button('Cerrar sesión'):
        st.session_state.pop('user', None)
        st.rerun()
    return user
