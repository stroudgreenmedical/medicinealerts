import { Outlet, Link, useLocation } from 'react-router-dom';
import {
  AppBar,
  Box,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  Button,
  Badge,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  Warning as AlertIcon,
  Analytics as AnalyticsIcon,
  Logout as LogoutIcon,
  Notifications as NotificationsIcon,
} from '@mui/icons-material';
import { useState, useEffect } from 'react';
import { dashboardApi } from '../services/api';

interface LayoutProps {
  onLogout: () => void;
}

const drawerWidth = 240;

function Layout({ onLogout }: LayoutProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [urgentCount, setUrgentCount] = useState(0);
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  useEffect(() => {
    // Fetch urgent alerts count
    const fetchUrgentCount = async () => {
      try {
        const stats = await dashboardApi.getStats();
        setUrgentCount(stats.urgent_alerts);
      } catch (error) {
        console.error('Failed to fetch urgent count:', error);
      }
    };

    fetchUrgentCount();
    // Refresh every 5 minutes
    const interval = setInterval(fetchUrgentCount, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const menuItems = [
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
    { text: 'Alerts', icon: <AlertIcon />, path: '/alerts' },
    { text: 'Analytics', icon: <AnalyticsIcon />, path: '/analytics' },
  ];

  const drawer = (
    <div>
      <Toolbar>
        <Typography variant="h6" noWrap>
          Medicines Alerts
        </Typography>
      </Toolbar>
      <List>
        {menuItems.map((item) => (
          <ListItem key={item.text} disablePadding>
            <ListItemButton
              component={Link}
              to={item.path}
              selected={location.pathname === item.path}
              sx={{
                '&.Mui-selected': {
                  backgroundColor: theme.palette.primary.main,
                  color: 'white',
                  '& .MuiListItemIcon-root': {
                    color: 'white',
                  },
                  '&:hover': {
                    backgroundColor: theme.palette.primary.dark,
                  },
                },
              }}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </div>
  );

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            Medicines Alerts Manager
          </Typography>
          
          <Badge badgeContent={urgentCount} color="error" sx={{ mr: 2 }}>
            <NotificationsIcon />
          </Badge>
          
          <Typography variant="body2" sx={{ mr: 2 }}>
            Dr Anjan Chakraborty
          </Typography>
          
          <Button color="inherit" startIcon={<LogoutIcon />} onClick={onLogout}>
            Logout
          </Button>
        </Toolbar>
      </AppBar>
      
      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
      >
        <Drawer
          variant={isMobile ? 'temporary' : 'permanent'}
          open={isMobile ? mobileOpen : true}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true, // Better open performance on mobile
          }}
          sx={{
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
            },
          }}
        >
          {drawer}
        </Drawer>
      </Box>
      
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          mt: 8,
        }}
      >
        <Outlet />
      </Box>
    </Box>
  );
}

export default Layout;